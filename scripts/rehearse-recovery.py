"""Replacement-VM rehearsal. Refuses existing stores, live engines and external routes."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import secrets
import subprocess
import tarfile
import time
from types import SimpleNamespace

D = ['docker', '--host', 'unix:///var/run/docker.sock']


def require(value, message):
    if not value:
        raise ValueError(message)


def output(args, **kwargs):
    return subprocess.check_output(args, text=True, **kwargs).strip()


def guard(expected):
    require(output(D+['info', '--format', '{{.ID}}']) == expected, 'Wrong recovery engine identity')
    require(output(D+['info', '--format', '{{.Name}}']) != 'relicrat-worker', 'Live worker is forbidden')
    for args in [['image','ls','-aq'], ['ps','-aq'], ['volume','ls','-q']]:
        require(not output(D+args), 'Recovery engine must be independently empty')
    for family in [[], ['-6']]:
        require(not any(r.get('dst') == 'default' for r in json.loads(output(['ip',*family,'-j','route']))), 'Recovery VM must have no external default route')


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def start_private_services(compose):
    subprocess.run(compose+['up','-d','--wait','db'], check=True, stdout=subprocess.DEVNULL)
    subprocess.run(compose+['up','-d','api','web'], check=True, stdout=subprocess.DEVNULL)


def rehearse(args):
    guard(args.expected_engine)
    require(not args.destination.exists(), 'Use a fresh rehearsal destination')
    capsule = module('capsule', Path(__file__).with_name('recovery-capsule.py'))
    images = capsule.validate(args.capsule, args.source_commit, args.source_sha256)
    args.destination.mkdir(mode=0o700)
    receipt = {'status':'started', 'source_commit':args.source_commit, 'engine_id':args.expected_engine, 'independently_empty_engine_verified':True, 'no_external_default_route':True, 'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
    path = args.destination/'receipt.json'
    def save():
        path.write_text(json.dumps(receipt, indent=2))
        path.chmod(0o600)
    save()
    source = args.destination/'source'
    source.mkdir(mode=0o700)
    with tarfile.open(args.capsule/'source.tar') as tar:
        capsule.members(tar)
        tar.extractall(source, filter='data')
    backup = module('recovered_backup', source/'scripts/backup.py')
    backup.DOCKER = D
    absent = args.destination/'must-not-exist'
    try:
        backup.restore(SimpleNamespace(directory=args.capsule/'backup', destination=absent))
    except subprocess.CalledProcessError:
        require(not absent.exists() and not output(D+['ps','-aq']) and not output(D+['volume','ls','-q']), 'Missing-image rejection created resources')
    else:
        raise ValueError('Restore incorrectly accepted missing images')
    receipt['missing_image_rejection_verified'] = True
    subprocess.run(D+['image','load','--input',str(args.capsule/'images.tar.gz')], check=True, stdout=subprocess.DEVNULL)
    for ident in images.values():
        require(output(D+['image','inspect','--format','{{.Id}}',ident]) == ident, 'Saved image identity changed')
    receipt['exact_images_loaded'] = True
    save()
    restored = args.destination/'restored'
    backup.restore(SimpleNamespace(directory=args.capsule/'backup', destination=restored))
    state = json.loads((restored/'restore.json').read_text())
    require(state['status'] == 'verified' and Path(state['compose']) == restored/'compose.json', 'Restore verification failed')
    receipt.update(offline_rows_migration_media_verified=True, restore_project=state['project'])
    save()
    C = D+['compose','-p',state['project'],'-f',state['compose']]
    if args.start_private_app:
        model = json.loads(Path(state['compose']).read_text())
        password = secrets.token_urlsafe(32)
        hashed = output(D+['run','--rm','-i','--network','none','--entrypoint','python',images['api'],'-c','import sys;from relicrat.credentials import hash_password;print(hash_password(sys.stdin.read()))'], input=password)
        model['services']['api']['environment'].update(RELICRAT_OWNER_PASSWORD_HASH=hashed.replace('$','$$'), RELICRAT_SESSION_SECRET=secrets.token_hex(32))
        model['services']['web'] = {'image':images['web'], 'environment':{'RELICRAT_API_URL':'http://api:8000','RELICRAT_WEB_ORIGIN':'http://127.0.0.1:3000','RELICRAT_ALLOW_LOOPBACK_HTTP':'1'}}
        for service in model['services'].values():
            service['restart'] = 'unless-stopped'
        Path(state['compose']).write_text(json.dumps(model))
        start_private_services(C)
        web = output(C+['ps','-q','web'])
        for _ in range(60):
            result = subprocess.run(D+['exec',web,'node','-e',"fetch('http://127.0.0.1:3000/login').then(r=>process.exit(r.status===200?0:1)).catch(()=>process.exit(1))"], capture_output=True)
            if result.returncode == 0:
                break
            time.sleep(1)
        else:
            raise ValueError('Recovered web did not become ready')
        auth = '''let input='';for await(const chunk of process.stdin)input+=chunk;const password=JSON.parse(input).password;const origin='http://127.0.0.1:3000';const guest=await fetch(origin+'/api/v1/inventory');const login=await fetch(origin+'/api/v1/auth/login',{method:'POST',headers:{Origin:origin,'Content-Type':'application/json'},body:JSON.stringify({password})});const cookie=login.headers.get('set-cookie')?.split(';')[0];if(!cookie)throw new Error('Missing owner cookie');const signed=await fetch(origin+'/api/v1/inventory',{headers:{Cookie:cookie}});console.log(JSON.stringify({guest:guest.status,login:login.status,signed:signed.status}));'''
        result = json.loads(output(D+['exec','-i',web,'node','--input-type=module','-e',auth], input=json.dumps({'password':password})))
        require(result == {'guest':401,'login':200,'signed':200}, 'Replacement owner boundary failed')
        receipt.update(fresh_owner_configuration_generated=True, captured_sessions_not_reused=True, private_application_checks=result)
        # A deliberate stop must survive daemon restart; running DB/API recover.
        subprocess.run(C+['stop','web'], check=True, stdout=subprocess.DEVNULL)
        subprocess.run(['systemctl','restart','docker'], check=True)
        require(not json.loads(output(D+['inspect',web]))[0]['State']['Running'], 'Intentional stop was not preserved')
        subprocess.run(C+['start','web'], check=True, stdout=subprocess.DEVNULL)
        for ident in output(C+['ps','-q']).split():
            item = json.loads(output(D+['inspect',ident]))[0]
            require(not item['HostConfig']['PortBindings'] and item['State']['Running'], 'Unexpected exposure or failed restart')
        receipt.update(unless_stopped_policy_verified=True, no_published_ports=True)
        save()
    for ident in output(D+['network','ls','-q','--filter','label=com.docker.compose.project='+state['project']]).split():
        require(json.loads(output(D+['network','inspect',ident]))[0]['Internal'], 'Restore network is not internal')
    subprocess.run(C+['down','--volumes'], check=True, stdout=subprocess.DEVNULL)
    for command in [['ps','-aq'],['volume','ls','-q'],['network','ls','-q']]:
        require(not output(D+command+['--filter','label=com.docker.compose.project='+state['project']]), 'Owned restore resources remain')
    receipt.update(status='verified-and-cleaned', owned_restore_resources_removed=True)
    save()
    print('Replacement VM recovery verified; private receipt saved')


def main():
    p = argparse.ArgumentParser(description=__doc__ + " Success removes this rehearsal's restored volumes; never use for a recovery you intend to retain.")
    p.add_argument('--expected-engine', required=True)
    p.add_argument('--capsule', type=Path, required=True)
    p.add_argument('--destination', type=Path, required=True)
    p.add_argument('--source-commit', required=True)
    p.add_argument('--source-sha256', required=True)
    p.add_argument('--start-private-app', action='store_true')
    a = p.parse_args()
    os.umask(0o077)
    rehearse(a)


if __name__ == '__main__':
    main()
