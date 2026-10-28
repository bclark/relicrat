"""Use the real login path for existing domain test clients."""
PASSWORD = 'synthetic-only-owner-password'


def sign_in(client):
    response = client.post('/api/v1/auth/login', json={'password': PASSWORD})
    assert response.status_code == 200, response.text
    client.headers['Authorization'] = 'Bearer ' + response.json()['token']
