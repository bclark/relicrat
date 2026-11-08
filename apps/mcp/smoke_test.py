"""Drive the stdio server from an MCP client against the disposable CI API."""

import asyncio
import os
import sys
from pathlib import Path
from uuid import uuid4

import httpx
from mcp import Client
from mcp.client.stdio import StdioServerParameters

ORIGIN = 'http://127.0.0.1:8000'


async def main():
    if os.getenv('RELICRAT_TEST_DISPOSABLE_MCP_API') != '1':
        raise SystemExit('Run only against a disposable RelicRat API.')
    with httpx.Client(base_url=ORIGIN, trust_env=False) as owner:
        def post(path, payload=None):
            result = owner.post('/api/v1/' + path, json=payload)
            result.raise_for_status()
            return result.json()

        session = post('auth/login', {'password': 'synthetic-only-owner-password'})
        owner.headers['Authorization'] = 'Bearer ' + session['token']
        box = post('storage-locations', {'name': 'Synthetic MCP box'})
        copy = post('inventory', {'title': 'Synthetic MCP copy'})
        post(f"inventory/{copy['id']}/location",
             {'storage_location_id': box['id'], 'expected_storage_revision': 0})
        audit_path = f"/api/v1/storage-locations/{box['id']}/audits"
        preview = owner.get(audit_path)
        preview.raise_for_status()
        post(audit_path.removeprefix('/api/v1/'), {
            'request_id': str(uuid4()), 'snapshot': preview.json()['snapshot'],
            'found_ids': [], 'extras': ['Synthetic MCP extra'],
        })
        token = post('auth/agent-credential')['token']
        params = StdioServerParameters(
            command=sys.executable, args=[str(Path(__file__).with_name('server.py').resolve())],
            env={'RELICRAT_API_ORIGIN': ORIGIN, 'RELICRAT_AGENT_TOKEN': token},
        )
        async with Client(params, read_timeout_seconds=15) as agent:
            tools = (await agent.list_tools()).tools
            assert {tool.name for tool in tools} == {
                'search_collection', 'get_copy_location', 'list_unresolved_audit_findings',
            }
            assert all(tool.annotations.read_only_hint for tool in tools)
            expected = {'id': copy['id'], 'title': copy['title'], 'edition': None,
                        'location': {'id': box['id'], 'name': box['name']}}
            search = await agent.call_tool('search_collection', {'query': copy['title'], 'limit': 1})
            assert not search.is_error and search.structured_content == {'copies': [expected]}
            location = await agent.call_tool('get_copy_location', {'copy_id': copy['id']})
            assert not location.is_error and location.structured_content == expected
            findings = await agent.call_tool('list_unresolved_audit_findings')
            assert not findings.is_error
            assert {'id': box['id'], 'name': box['name'], 'unresolved': 2} in findings.structured_content['locations']
            revoked = owner.delete('/api/v1/auth/agent-credential')
            revoked.raise_for_status()
            denied = await agent.call_tool('get_copy_location', {'copy_id': copy['id']})
            assert denied.is_error and 'denied access' in denied.content[0].text
            assert token not in denied.content[0].text
    print('MCP collection search, copy location, audit findings, and revocation passed')


if __name__ == '__main__':
    asyncio.run(main())
