import { User, WebStorageStateStore } from "oidc-client-ts";
import type { AuthProviderProps } from "react-oidc-context";

const authority = import.meta.env.VITE_OIDC_AUTHORITY;
const clientId = import.meta.env.VITE_OIDC_CLIENT_ID;

export const oidcConfig: AuthProviderProps = {
  authority,
  client_id: clientId,
  redirect_uri: window.location.origin,
  post_logout_redirect_uri: window.location.origin,
  scope: "openid profile",
  userStore: new WebStorageStateStore({ store: window.sessionStorage }),
  // Убираем ?code=... из адресной строки после входа
  onSigninCallback: () => window.history.replaceState({}, document.title, window.location.pathname),
};

/** Токен для API-клиента вне React-контекста. */
export function getAccessToken(): string | undefined {
  const raw = sessionStorage.getItem(`oidc.user:${authority}:${clientId}`);
  return raw ? User.fromStorageString(raw).access_token : undefined;
}
