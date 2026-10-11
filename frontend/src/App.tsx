import { AppShell, Button, Center, Group, Loader, NavLink, Title } from "@mantine/core";
import { useAuth } from "react-oidc-context";
import { Link, Navigate, Route, Routes, useLocation } from "react-router-dom";

import AuditPage from "./pages/AuditPage";
import CIDetailPage from "./pages/CIDetailPage";
import CIListPage from "./pages/CIListPage";
import ImportPage from "./pages/ImportPage";
import TypesPage from "./pages/TypesPage";

const NAV = [
  { to: "/cis", label: "Конфигурационные единицы" },
  { to: "/import", label: "Импорт" },
  { to: "/audit", label: "История изменений" },
  { to: "/admin/types", label: "Типы (админ)" },
];

export default function App() {
  const auth = useAuth();
  const { pathname } = useLocation();

  if (auth.isLoading) {
    return (
      <Center h="100vh">
        <Loader />
      </Center>
    );
  }
  if (!auth.isAuthenticated) {
    return (
      <Center h="100vh">
        <Button onClick={() => auth.signinRedirect()}>Войти через SSO</Button>
      </Center>
    );
  }

  return (
    <AppShell header={{ height: 56 }} navbar={{ width: 260, breakpoint: "sm" }} padding="md">
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Title order={3}>CMDB</Title>
          <Group>
            {auth.user?.profile.preferred_username}
            <Button variant="subtle" onClick={() => auth.signoutRedirect()}>
              Выйти
            </Button>
          </Group>
        </Group>
      </AppShell.Header>
      <AppShell.Navbar p="xs">
        {NAV.map((n) => (
          <NavLink key={n.to} component={Link} to={n.to} label={n.label} active={pathname.startsWith(n.to)} />
        ))}
      </AppShell.Navbar>
      <AppShell.Main>
        <Routes>
          <Route path="/" element={<Navigate to="/cis" replace />} />
          <Route path="/cis" element={<CIListPage />} />
          <Route path="/cis/:id" element={<CIDetailPage />} />
          <Route path="/import" element={<ImportPage />} />
          <Route path="/audit" element={<AuditPage />} />
          <Route path="/admin/types" element={<TypesPage />} />
        </Routes>
      </AppShell.Main>
    </AppShell>
  );
}
