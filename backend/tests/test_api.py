import uuid

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def unique_user(prefix: str):
    suffix = uuid.uuid4().hex[:8]
    return {
        'email': f'{prefix}-{suffix}@example.com',
        'username': f'{prefix}-{suffix}',
        'password': 'StrongPass123!',
    }


def test_health():
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'


def test_auth_and_workspace_flow():
    user = unique_user('api-user')
    resp = client.post('/auth/register', json=user)
    assert resp.status_code == 200
    token = resp.json()['access_token']
    headers = {'Authorization': f'Bearer {token}'}

    workspace = client.post('/workspaces', json={'name': 'Test Workspace'}, headers=headers)
    assert workspace.status_code == 200
    workspace_id = workspace.json()['id']

    note = client.post(f'/workspaces/{workspace_id}/notes', json={'title': 'Plan', 'content': 'Ship it'}, headers=headers)
    assert note.status_code == 200
    note_id = note.json()['id']

    docs = client.get(f'/workspaces/{workspace_id}/documents', headers=headers)
    assert docs.status_code == 200

    chat = client.post(
        f'/workspaces/{workspace_id}/ai/chat',
        json={'message': 'What is the plan?', 'limit': 5},
        headers=headers,
    )
    assert chat.status_code == 200
    assert 'answer' in chat.json()

    resp = client.get('/workspaces', headers=headers)
    assert resp.status_code == 200
    assert any(item['id'] == workspace_id for item in resp.json())

    resp = client.delete(f'/workspaces/{workspace_id}/notes/{note_id}', headers=headers)
    assert resp.status_code == 204

    resp = client.delete(f'/workspaces/{workspace_id}', headers=headers)
    assert resp.status_code == 204


def test_cross_user_forbidden():
    user_a = unique_user('cross-a')
    user_b = unique_user('cross-b')
    created_a = client.post('/auth/register', json=user_a)
    created_b = client.post('/auth/register', json=user_b)
    assert created_a.status_code == 200
    assert created_b.status_code == 200

    token_a = created_a.json()['access_token']
    token_b = created_b.json()['access_token']

    workspace = client.post('/workspaces', json={'name': 'Secret'}, headers={'Authorization': f'Bearer {token_a}'})
    workspace_id = workspace.json()['id']

    resp = client.get(f'/workspaces/{workspace_id}', headers={'Authorization': f'Bearer {token_b}'})
    assert resp.status_code == 404
