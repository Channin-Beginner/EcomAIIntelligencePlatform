import http from './http'

const SESSION_KEY = 'ecom_session_id'

function createSessionId(): string {
  // randomUUID only exists in secure contexts (HTTPS / localhost), not on LAN HTTP IPs.
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2, 11)}`
}

export function getSessionId(): string {
  let id = sessionStorage.getItem(SESSION_KEY)
  if (!id) {
    id = createSessionId()
    sessionStorage.setItem(SESSION_KEY, id)
  }
  return id
}

/** Implicit behavior only — explicit actions (cart/fav) are logged server-side. */
export function trackEvent(eventType: 'pv' | 'click', productId?: number) {
  return http.post('/event/track', {
    eventType,
    productId,
    sessionId: getSessionId(),
    pagePath: window.location.pathname,
  })
}
