'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';

type User = { id: number; email: string; username: string };
type Workspace = {
  id: number;
  name: string;
  description?: string | null;
  owner_id: number;
  created_at: string;
  updated_at: string;
};
type Note = {
  id: number;
  title: string;
  content?: string | null;
  workspace_id: number;
  created_at: string;
  updated_at: string;
};
type DocumentItem = {
  id: number;
  title: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  storage_path: string;
  text_content?: string | null;
  workspace_id: number;
  owner_id: number;
  created_at: string;
  updated_at: string;
};
type ChatResponse = { answer: string; sources: string[]; score: number };

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const TOKEN_KEY = 'ai_workspace_token';

async function apiFetch<T>(path: string, init: RequestInit = {}, token?: string): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      ...(init.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init.headers || {}),
    },
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || 'Request failed');
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export default function HomePage() {
  const [token, setToken] = useState<string | null>(() => {
    if (typeof window === 'undefined') {
      return null;
    }
    return window.localStorage.getItem(TOKEN_KEY);
  });
  const [user, setUser] = useState<User | null>(null);
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [selectedWorkspace, setSelectedWorkspace] = useState<Workspace | null>(null);
  const [notes, setNotes] = useState<Note[]>([]);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [chatText, setChatText] = useState('');
  const [chatResponse, setChatResponse] = useState<ChatResponse | null>(null);
  const [workspaceName, setWorkspaceName] = useState('');
  const [workspaceDescription, setWorkspaceDescription] = useState('');
  const [noteTitle, setNoteTitle] = useState('');
  const [noteContent, setNoteContent] = useState('');
  const [uploadTitle, setUploadTitle] = useState('');
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);

  const loadWorkspaceData = useCallback(async (workspaceId: number, currentToken: string) => {
    const [notesData, documentsData] = await Promise.all([
      apiFetch<Note[]>(`/workspaces/${workspaceId}/notes`, {}, currentToken),
      apiFetch<DocumentItem[]>(`/workspaces/${workspaceId}/documents`, {}, currentToken),
    ]);
    setNotes(notesData);
    setDocuments(documentsData);
  }, []);

  const loadWorkspaces = useCallback(async (currentToken: string) => {
    const response = await apiFetch<Workspace[]>('/workspaces', {}, currentToken);
    setWorkspaces(response);
    if (!selectedWorkspace && response[0]) {
      setSelectedWorkspace(response[0]);
      await loadWorkspaceData(response[0].id, currentToken);
    }
  }, [loadWorkspaceData, selectedWorkspace]);

  const loadCurrentUser = useCallback(async (currentToken: string) => {
    try {
      const response = await apiFetch<{ id: number; email: string; username: string }>('/users/me', {}, currentToken);
      setUser(response);
      await loadWorkspaces(currentToken);
    } catch {
      setToken(null);
      window.localStorage.removeItem(TOKEN_KEY);
    }
  }, [loadWorkspaces]);

  useEffect(() => {
    if (!token) {
      return;
    }
    void loadCurrentUser(token);
  }, [loadCurrentUser, token]);

  const currentWorkspaceName = useMemo(() => selectedWorkspace?.name || 'No workspace selected', [selectedWorkspace]);

  async function handleAuthSubmit(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError('');
    try {
      const endpoint = mode === 'login' ? '/auth/login' : '/auth/register';
      const payload = mode === 'login' ? { email, password } : { email, username, password };
      const response = await apiFetch<{ access_token: string; user: User }>(endpoint, {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      setToken(response.access_token);
      setUser(response.user);
      window.localStorage.setItem(TOKEN_KEY, response.access_token);
      await loadWorkspaces(response.access_token);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Authentication failed');
    } finally {
      setLoading(false);
    }
  }

  async function handleCreateWorkspace() {
    if (!token || !workspaceName.trim()) return;
    try {
      const created = await apiFetch<Workspace>('/workspaces', {
        method: 'POST',
        body: JSON.stringify({ name: workspaceName, description: workspaceDescription }),
      }, token);
      setWorkspaces((current) => [created, ...current]);
      setSelectedWorkspace(created);
      setWorkspaceName('');
      setWorkspaceDescription('');
      await loadWorkspaceData(created.id, token);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Unable to create workspace');
    }
  }

  async function handleCreateNote() {
    if (!token || !selectedWorkspace || !noteTitle.trim()) return;
    try {
      const created = await apiFetch<Note>(`/workspaces/${selectedWorkspace.id}/notes`, {
        method: 'POST',
        body: JSON.stringify({ title: noteTitle, content: noteContent }),
      }, token);
      setNotes((current) => [created, ...current]);
      setNoteTitle('');
      setNoteContent('');
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Unable to create note');
    }
  }

  async function handleUploadDocument() {
    if (!token || !selectedWorkspace || !uploadFile) return;
    try {
      const formData = new FormData();
      formData.append('file', uploadFile);
      if (uploadTitle.trim()) formData.append('title', uploadTitle);
      const created = await apiFetch<DocumentItem>(`/workspaces/${selectedWorkspace.id}/documents`, {
        method: 'POST',
        body: formData,
      }, token);
      setDocuments((current) => [created, ...current]);
      setUploadFile(null);
      setUploadTitle('');
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Unable to upload document');
    }
  }

  async function handleChat() {
    if (!token || !selectedWorkspace || !chatText.trim()) return;
    try {
      const response = await apiFetch<ChatResponse>(`/workspaces/${selectedWorkspace.id}/ai/chat`, {
        method: 'POST',
        body: JSON.stringify({ message: chatText, limit: 5 }),
      }, token);
      setChatResponse(response);
      setChatText('');
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Unable to chat');
    }
  }

  if (!token || !user) {
    return (
      <main className="min-h-screen flex items-center justify-center bg-slate-950 px-4 py-12">
        <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900 p-8 shadow-2xl shadow-slate-950/40">
          <div className="mb-6 text-center">
            <p className="text-xs uppercase tracking-[0.3em] text-cyan-400">AI Workspace</p>
            <h1 className="mt-3 text-3xl font-bold text-white">Secure knowledge workspace</h1>
          </div>

          <div className="mb-5 inline-flex rounded-full bg-slate-800 p-1">
            <button type="button" className={`rounded-full px-4 py-2 text-sm font-medium ${mode === 'login' ? 'bg-cyan-500 text-slate-950' : 'text-slate-300'}`} onClick={() => setMode('login')}>Login</button>
            <button type="button" className={`rounded-full px-4 py-2 text-sm font-medium ${mode === 'register' ? 'bg-cyan-500 text-slate-950' : 'text-slate-300'}`} onClick={() => setMode('register')}>Register</button>
          </div>

          <form onSubmit={handleAuthSubmit} className="space-y-4">
            {mode === 'register' && (
              <label className="block text-sm text-slate-300">
                Username
                <input className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-white outline-none focus:border-cyan-400" value={username} onChange={(event) => setUsername(event.target.value)} />
              </label>
            )}
            <label className="block text-sm text-slate-300">
              Email
              <input type="email" className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-white outline-none focus:border-cyan-400" value={email} onChange={(event) => setEmail(event.target.value)} />
            </label>
            <label className="block text-sm text-slate-300">
              Password
              <input type="password" className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-white outline-none focus:border-cyan-400" value={password} onChange={(event) => setPassword(event.target.value)} />
            </label>
            {error && <p className="text-sm text-rose-400">{error}</p>}
            <button type="submit" disabled={loading} className="w-full rounded-lg bg-cyan-500 px-4 py-2 font-semibold text-slate-950 hover:bg-cyan-400 disabled:opacity-60">
              {loading ? 'Working...' : mode === 'login' ? 'Sign in' : 'Create account'}
            </button>
          </form>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-950 px-4 py-8">
      <div className="mx-auto max-w-7xl">
        <header className="mb-8 flex flex-col gap-4 rounded-2xl border border-slate-800 bg-slate-900/80 p-5 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-cyan-400">Workspace</p>
            <h1 className="mt-2 text-3xl font-bold text-white">{currentWorkspaceName}</h1>
          </div>
          <div className="flex items-center gap-3">
            <div className="rounded-full border border-slate-700 bg-slate-800 px-3 py-1 text-sm text-slate-200">{user.username}</div>
            <button
              type="button"
              className="rounded-full border border-slate-700 px-4 py-2 text-sm font-medium text-slate-200 hover:bg-slate-800"
              onClick={() => {
                setToken(null);
                setUser(null);
                setSelectedWorkspace(null);
                window.localStorage.removeItem(TOKEN_KEY);
              }}
            >
              Sign out
            </button>
          </div>
        </header>

        <div className="grid gap-6 xl:grid-cols-[260px_minmax(0,1fr)]">
          <aside className="space-y-6 rounded-2xl border border-slate-800 bg-slate-900 p-5">
            <div>
              <h2 className="text-lg font-semibold text-white">Workspaces</h2>
              <div className="mt-4 space-y-2">
                {workspaces.map((workspace) => (
                  <button
                    key={workspace.id}
                    type="button"
                    className={`w-full rounded-xl border px-3 py-2 text-left transition ${selectedWorkspace?.id === workspace.id ? 'border-cyan-500 bg-cyan-500/10 text-cyan-200' : 'border-slate-700 bg-slate-800 text-slate-200 hover:border-slate-600'}`}
                    onClick={async () => {
                      setSelectedWorkspace(workspace);
                      if (token) await loadWorkspaceData(workspace.id, token);
                    }}
                  >
                    <div className="font-medium">{workspace.name}</div>
                    <div className="mt-1 text-xs text-slate-400">{workspace.description || 'No description'}</div>
                  </button>
                ))}
              </div>
            </div>

            <div className="rounded-xl border border-slate-700 bg-slate-800 p-3">
              <label className="block text-sm text-slate-300">Workspace name</label>
              <input value={workspaceName} onChange={(event) => setWorkspaceName(event.target.value)} className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white" />
              <label className="mt-3 block text-sm text-slate-300">Description</label>
              <textarea value={workspaceDescription} onChange={(event) => setWorkspaceDescription(event.target.value)} className="mt-2 min-h-20 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white" />
              <button type="button" onClick={handleCreateWorkspace} className="mt-3 w-full rounded-lg bg-cyan-500 px-3 py-2 font-medium text-slate-950">Create workspace</button>
            </div>
          </aside>

          <section className="space-y-6">
            <div className="grid gap-6 lg:grid-cols-2">
              <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
                <h2 className="text-lg font-semibold text-white">Notes</h2>
                <div className="mt-4 space-y-3 rounded-xl border border-slate-700 bg-slate-800 p-3">
                  <input value={noteTitle} onChange={(event) => setNoteTitle(event.target.value)} placeholder="Note title" className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white" />
                  <textarea value={noteContent} onChange={(event) => setNoteContent(event.target.value)} placeholder="Write your note..." className="min-h-24 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white" />
                  <button type="button" onClick={handleCreateNote} className="w-full rounded-lg bg-indigo-500 px-3 py-2 font-medium text-white">Save note</button>
                </div>
                <div className="mt-4 space-y-3">
                  {notes.length === 0 && <p className="text-sm text-slate-400">No notes yet in this workspace.</p>}
                  {notes.map((note) => (
                    <div key={note.id} className="rounded-xl border border-slate-700 bg-slate-800 p-3">
                      <div className="font-semibold text-white">{note.title}</div>
                      <p className="mt-2 text-sm text-slate-300">{note.content || 'No content yet.'}</p>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
                <h2 className="text-lg font-semibold text-white">Documents</h2>
                <div className="mt-4 space-y-3 rounded-xl border border-slate-700 bg-slate-800 p-3">
                  <input value={uploadTitle} onChange={(event) => setUploadTitle(event.target.value)} placeholder="Document title" className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white" />
                  <input type="file" onChange={(event) => setUploadFile(event.target.files?.[0] || null)} className="w-full text-sm text-slate-300" />
                  <button type="button" onClick={handleUploadDocument} className="w-full rounded-lg bg-emerald-500 px-3 py-2 font-medium text-slate-950">Upload</button>
                </div>
                <div className="mt-4 space-y-3">
                  {documents.length === 0 && <p className="text-sm text-slate-400">No uploaded documents.</p>}
                  {documents.map((document) => (
                    <div key={document.id} className="rounded-xl border border-slate-700 bg-slate-800 p-3">
                      <div className="flex items-center justify-between gap-2">
                        <div className="font-medium text-white">{document.title}</div>
                        <span className="rounded-full bg-slate-700 px-2 py-1 text-[10px] uppercase tracking-wide text-slate-300">{document.content_type}</span>
                      </div>
                      <div className="mt-2 text-xs text-slate-400">{document.filename}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
              <h2 className="text-lg font-semibold text-white">AI assistant</h2>
              <div className="mt-4 flex flex-col gap-3 md:flex-row">
                <input value={chatText} onChange={(event) => setChatText(event.target.value)} placeholder="Ask a question about this workspace..." className="flex-1 rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-white" />
                <button type="button" onClick={handleChat} className="rounded-lg bg-cyan-500 px-4 py-2 font-medium text-slate-950">Ask</button>
              </div>
              {chatResponse && (
                <div className="mt-4 rounded-xl border border-cyan-500/40 bg-cyan-500/5 p-4 text-slate-200">
                  <div className="text-sm text-cyan-300">Relevance score: {chatResponse.score.toFixed(3)}</div>
                  <p className="mt-3 whitespace-pre-wrap text-sm leading-6">{chatResponse.answer}</p>
                  {chatResponse.sources.length > 0 && (
                    <div className="mt-3 text-xs text-slate-300">
                      Sources: {chatResponse.sources.join(', ')}
                    </div>
                  )}
                </div>
              )}
            </div>
          </section>
        </div>
      </div>
    </main>
  );
}
