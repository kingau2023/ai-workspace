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


def test_document_upload_and_chat_flow():
    user = unique_user('doc-user')
    created = client.post('/auth/register', json=user)
    assert created.status_code == 200
    token = created.json()['access_token']
    headers = {'Authorization': f'Bearer {token}'}

    workspace = client.post('/workspaces', json={'name': 'Docs Workspace'}, headers=headers)
    assert workspace.status_code == 200
    workspace_id = workspace.json()['id']

    upload = client.post(
        f'/workspaces/{workspace_id}/documents',
        headers=headers,
        files={'file': ('research.txt', b'AI research on knowledge graphs and retrieval augmentation.', 'text/plain')},
        data={'title': 'Research Notes'},
    )
    assert upload.status_code == 200
    document_id = upload.json()['id']

    list_response = client.get(f'/workspaces/{workspace_id}/documents', headers=headers)
    assert list_response.status_code == 200
    assert any(item['id'] == document_id for item in list_response.json())

    chat = client.post(
        f'/workspaces/{workspace_id}/ai/chat',
        json={'message': 'What is the research about?', 'limit': 5},
        headers=headers,
    )
    assert chat.status_code == 200
    payload = chat.json()
    assert payload['score'] >= 0.0
    assert 'knowledge' in payload['answer'].lower() or 'research' in payload['answer'].lower()

    delete_response = client.delete(f'/workspaces/{workspace_id}/documents/{document_id}', headers=headers)
    assert delete_response.status_code == 204


def test_invalid_inputs_and_upload_limits():
    user = unique_user('limits-user')
    created = client.post('/auth/register', json=user)
    assert created.status_code == 200
    token = created.json()['access_token']
    headers = {'Authorization': f'Bearer {token}'}

    workspace = client.post('/workspaces', json={'name': 'Validate'}, headers=headers)
    assert workspace.status_code == 200
    workspace_id = workspace.json()['id']

    blank_workspace = client.post('/workspaces', json={'name': ''}, headers=headers)
    assert blank_workspace.status_code == 422

    blank_note = client.post(f'/workspaces/{workspace_id}/notes', json={'title': ''}, headers=headers)
    assert blank_note.status_code == 422

    oversized = client.post(
        f'/workspaces/{workspace_id}/documents',
        headers=headers,
        files={'file': ('big.txt', b'a' * 11000000, 'text/plain')},
    )
    assert oversized.status_code == 413

    invalid_type = client.post(
        f'/workspaces/{workspace_id}/documents',
        headers=headers,
        files={'file': ('bad.bin', b'not-a-text-file', 'application/x-msdownload')},
    )
    assert invalid_type.status_code == 400


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
