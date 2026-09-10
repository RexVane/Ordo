// @vitest-environment happy-dom

import { beforeEach, describe, expect, it } from 'vitest'

import { AUTH_SCOPE_CHANGED_EVENT, getAccessToken, setAccessToken } from '@/lib/auth-storage'
import { useDocumentView } from './document-view'

describe('document view auth scope', () => {
  beforeEach(() => {
    localStorage.clear()
    sessionStorage.clear()
  })

  it('drops persisted document context when the auth scope changes', () => {
    useDocumentView.getState().openDocument('private-doc', 'private-chunk', undefined, {
      sourceContext: {
        kind: 'chat-citation',
        messageId: 'message-1',
        documentId: 'private-doc',
        chunkContent: 'private content',
      },
    })

    window.dispatchEvent(new Event(AUTH_SCOPE_CHANGED_EVENT))

    expect(useDocumentView.getState()).toMatchObject({
      isOpen: false,
      documentId: null,
      sourceContext: null,
      documentLayouts: {},
      lastOpenedTarget: null,
    })
    expect(localStorage.getItem('ordo_document_view_v1')).toBeNull()
  })

  it('rejects persisted context from another tenant or user', async () => {
    localStorage.setItem('ordo_tenant_id', 'tenant-b')
    localStorage.setItem('ordo_user_id', 'user-b')
    localStorage.setItem('ordo_document_view_v1', JSON.stringify({
      state: {
        authScope: 'tenant-a:user-a',
        isOpen: true,
        documentId: 'private-doc',
        sourceContext: { chunkContent: 'private content' },
      },
      version: 0,
    }))

    await useDocumentView.persist.rehydrate()

    expect(useDocumentView.getState()).toMatchObject({
      isOpen: false,
      documentId: null,
      sourceContext: null,
    })
  })

  it('clears open source context when another tab changes user', () => {
    setAccessToken({ access_token: 'user-a-token', token_type: 'bearer', expires_in: 3600 })
    localStorage.setItem('ordo_user_id', 'user-a')
    useDocumentView.getState().openDocument('private-doc', 'private-chunk', undefined, {
      sourceContext: {
        kind: 'chat-citation',
        messageId: 'message-1',
        documentId: 'private-doc',
        chunkContent: 'private content',
      },
    })

    localStorage.setItem('ordo_user_id', 'user-b')
    window.dispatchEvent(
      new StorageEvent('storage', {
        key: 'ordo_user_id',
        oldValue: 'user-a',
        newValue: 'user-b',
      })
    )

    expect(useDocumentView.getState()).toMatchObject({
      authScope: 'default:anonymous',
      isOpen: false,
      documentId: null,
      sourceContext: null,
    })
    expect(getAccessToken()).toBeNull()
    expect(localStorage.getItem('ordo_document_view_v1')).toBeNull()
  })
})
