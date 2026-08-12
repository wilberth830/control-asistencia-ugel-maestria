import { ChangeEvent, FormEvent, ReactNode, useEffect, useRef, useState } from "react";
import {
  Navigate,
  NavLink,
  Route,
  Routes,
  useLocation,
  useNavigate,
} from "react-router-dom";

import apiClient, { SESSION_EXPIRED_EVENT } from "./services/apiClient";
import {
  importTouchesPeriod,
  monthsFromImports,
  yearsFromImports,
} from "./utils/periodUtils";

type AccessMap = {
  modules: string[];
  operations: Record<string, boolean>;
};

type Session = {
  token: string;
  username: string;
  role: string;
  access: AccessMap;
};

type DashboardIndicators = {
  total_uploaded_files: number;
  active_staff_members: number;
  period: { month: number; year: number };
  mark_distribution: Record<string, number>;
  recent_imports: Array<{
    id: number;
    file_name: string;
    status: string;
    period_start: string | null;
    period_end: string | null;
    total_rows: number;
  }>;
};

type StaffMember = {
  id: number;
  dni: string;
  last_names: string;
  first_names: string;
  job_title: string;
  employment_status: string | null;
  is_active: "Y" | "N";
};

let staffMembersCache: StaffMember[] | null = null;
let staffMembersRequest: Promise<StaffMember[]> | null = null;
let staffMembersCacheVersion = 0;

function loadStaffMembers(): Promise<StaffMember[]> {
  if (staffMembersCache) return Promise.resolve(staffMembersCache);
  if (staffMembersRequest) return staffMembersRequest;

  const requestVersion = staffMembersCacheVersion;
  const request: Promise<StaffMember[]> = apiClient
    .get<StaffMember[]>("/api/v1/staff-members")
    .then((response) => {
      if (requestVersion === staffMembersCacheVersion) {
        staffMembersCache = response.data;
      }
      return response.data;
    })
    .finally(() => {
      if (staffMembersRequest === request) staffMembersRequest = null;
    });
  staffMembersRequest = request;
  return request;
}

function clearStaffMembersCache() {
  staffMembersCacheVersion += 1;
  staffMembersCache = null;
  staffMembersRequest = null;
}

type ImportRow = {
  row_id: number;
  order: number;
  dni: string;
  last_names: string;
  first_names: string;
  marked_at?: string;
  mark_type?: string;
  match: "matched" | "new";
  staff_member_id: number | null;
  resolved?: boolean;
  skipped?: boolean;
};

type ImportRowDraft = {
  dni: string;
  last_names: string;
  first_names: string;
};

type BiometricImport = {
  id: number;
  file_name: string;
  status: "draft" | "confirmed" | "cancelled";
  period_start: string | null;
  period_end: string | null;
  total_rows: number;
  matched_rows: number;
  new_rows: number;
  ok_rows: number;
  error_rows: number;
  normalization_source?: "parser" | "local_fallback" | "openai";
  ai_estimated_cost_usd?: string;
  rows?: ImportRow[];
};

type AttendanceDay = {
  id: number;
  staff_member_id: number;
  biometric_import_id?: number | null;
  attendance_date: string;
  status: string;
  late_minutes: number;
  justification_id: number | null;
};

type Justification = {
  id: number;
  staff_member_id: number;
  start_date: string;
  end_date: string;
  norm_code: string;
  with_pay: "Y" | "N";
  reason: string | null;
  support_file_path: string | null;
  registered_at?: string | null;
  status: "active" | "cancelled";
  cancel_reason?: string | null;
};

const justificationNorms = [
  { code: "LG", label: "LG - Licencia con Goce" },
  { code: "LS", label: "LS - Licencia sin Goce" },
  { code: "P", label: "P - Permiso sin Goce" },
  { code: "J", label: "J - Inasistencia Justificada" },
  { code: "H", label: "H - Huelga / Paro" },
  { code: "F", label: "F - Feriado" },
] as const;

type Annex03Report = {
  institution: {
    ugel: string;
    school_name: string;
    modular_code: string;
    education_level: string;
    shift_name: string;
  };
  period: { month: number; year: number };
  rows: Array<{
    staff_member_id: number;
    dni: string;
    full_name: string;
    days: AttendanceDay[];
  }>;
};

type Annex04Report = {
  institution: {
    ugel: string;
    school_name: string;
    modular_code: string;
    education_level: string;
    shift_name: string;
  };
  period: { month: number; year: number };
  staff_count: number;
  totals: {
    present: number;
    late: number;
    absent: number;
    justified: number;
    leave: number;
    permission: number;
  };
};

type ReportPreview =
  | {
      type: "03";
      rows: Array<{
        dni: string;
        full_name: string;
        days: AttendanceDay[];
      }>;
    }
  | {
      type: "04";
      totals: Annex04Report["totals"];
      staff_count: number;
    };

const STORAGE_KEY = "chiquistrukis.session";
const REMEMBERED_USERNAME_KEY = "chiquistrukis.rememberedUsername";
const REMEMBER_PREFERENCE_KEY = "chiquistrukis.rememberMe";

const navigationItems = [
  { to: "/dashboard", label: "Dashboard", icon: "D", module: "dashboard" },
  { to: "/personal", label: "Personal", icon: "P", module: "personal" },
  { to: "/carga", label: "Carga biométrica", icon: "C", module: "asistencia_biometrica" },
  { to: "/asistencia", label: "Asistencia", icon: "A", module: "administracion_asistencia" },
  { to: "/justificaciones", label: "Justificaciones", icon: "J", module: "administracion_asistencia" },
  { to: "/reportes", label: "Reportes", icon: "R", module: "reportes_oficiales" },
];

function readStoredSession(): Session | null {
  for (const storage of [localStorage, sessionStorage]) {
    const raw = storage.getItem(STORAGE_KEY);
    if (!raw) continue;
    try {
      return JSON.parse(raw) as Session;
    } catch {
      storage.removeItem(STORAGE_KEY);
      storage.removeItem("token");
    }
  }
  return null;
}

function clearStoredSession() {
  for (const storage of [localStorage, sessionStorage]) {
    storage.removeItem(STORAGE_KEY);
    storage.removeItem("token");
  }
}

function App() {
  const [session, setSession] = useState<Session | null>(() => readStoredSession());
  const [sessionExpired, setSessionExpired] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    const expireSession = () => {
      clearStaffMembersCache();
      clearStoredSession();
      setSession(null);
      setSessionExpired(true);
    };

    window.addEventListener(SESSION_EXPIRED_EVENT, expireSession);
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, expireSession);
  }, []);

  const handleSession = (nextSession: Session | null, rememberSession = true) => {
    setSession(nextSession);
    if (nextSession) {
      setSessionExpired(false);
      clearStoredSession();
      const storage = rememberSession ? localStorage : sessionStorage;
      storage.setItem(STORAGE_KEY, JSON.stringify(nextSession));
      storage.setItem("token", nextSession.token);
      localStorage.setItem(REMEMBER_PREFERENCE_KEY, String(rememberSession));
      if (rememberSession) {
        localStorage.setItem(REMEMBERED_USERNAME_KEY, nextSession.username);
      } else {
        localStorage.removeItem(REMEMBERED_USERNAME_KEY);
      }
    } else {
      clearStaffMembersCache();
      clearStoredSession();
    }
  };

  const returnToLogin = () => {
    setSessionExpired(false);
    navigate("/login", { replace: true });
  };

  return (
    <>
      <Routes>
        <Route
          path="/login"
          element={
            session ? (
              <Navigate to="/dashboard" replace />
            ) : (
              <LoginPage onLogin={handleSession} />
            )
          }
        />
        <Route
          path="/*"
          element={
            session ? (
              <Shell session={session} onLogout={() => handleSession(null)} />
            ) : (
              <Navigate to="/login" replace />
            )
          }
        />
      </Routes>
      {sessionExpired && (
        <div className="modal-backdrop confirmation-backdrop" role="presentation">
          <section
            aria-labelledby="session-expired-title"
            aria-modal="true"
            className="confirmation-card"
            role="dialog"
          >
            <div className="confirmation-icon">!</div>
            <h2 id="session-expired-title">Sesión expirada</h2>
            <p>Tu token ha expirado. Vuelve a ingresar para continuar.</p>
            <div className="confirmation-actions">
              <button className="btn btn-primary" onClick={returnToLogin} type="button">
                Volver a ingresar
              </button>
            </div>
          </section>
        </div>
      )}
    </>
  );
}

function LoginPage({
  onLogin,
}: {
  onLogin: (session: Session, rememberSession: boolean) => void;
}) {
  const [username, setUsername] = useState(
    () => localStorage.getItem(REMEMBERED_USERNAME_KEY) ?? "director.demo",
  );
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(
    () => localStorage.getItem(REMEMBER_PREFERENCE_KEY) !== "false",
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const response = await apiClient.post<Session>("/api/v1/auth/sessions", {
        username,
        password,
      });
      onLogin(response.data, rememberMe);
      navigate("/dashboard", { replace: true });
    } catch {
      setError("No se pudo iniciar sesión");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="login-page">
      <form className="login-card" onSubmit={submit}>
        <div className="login-logo">CA</div>
        <h1>Control de Asistencia</h1>
        <p className="subtitle">Sistema biométrico · Instituciones educativas</p>
        <label className="form-field">
          <span>Usuario</span>
          <input
            autoComplete="username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
          />
        </label>
        <label className="form-field">
          <span>Contraseña</span>
          <input
            autoComplete="current-password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>
        <div className="login-row">
          <label>
            <input
              checked={rememberMe}
              onChange={(event) => setRememberMe(event.target.checked)}
              type="checkbox"
            />{" "}
            Recordarme
          </label>
          <span>Administrador UGEL</span>
        </div>
        {error && <div className="alert-danger">{error}</div>}
        <button className="btn btn-primary btn-lg" disabled={loading} type="submit">
          {loading ? "Ingresando" : "Iniciar sesión"}
        </button>
      </form>
    </main>
  );
}

function modulePage(session: Session, module: string, page: ReactNode) {
  return session.access.modules.includes(module) ? page : <Navigate to="/dashboard" replace />;
}

function Shell({
  session,
  onLogout,
}: {
  session: Session;
  onLogout: () => void;
}) {
  const location = useLocation();
  const [loggingOut, setLoggingOut] = useState(false);
  const title = navigationItems.find((item) =>
    location.pathname.startsWith(item.to),
  )?.label;

  useEffect(() => {
    void loadStaffMembers().catch(() => undefined);
  }, []);

  const logout = async () => {
    setLoggingOut(true);
    try {
      await apiClient.delete("/api/v1/auth/sessions/current");
    } finally {
      onLogout();
      setLoggingOut(false);
    }
  };

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="logo">CA</div>
          <span>
            Control de
            <br />
            Asistencia
          </span>
        </div>
        <nav className="sidebar-nav">
          {navigationItems
            .filter((item) => session.access.modules.includes(item.module))
            .map((item) => (
            <NavLink className="nav-item" key={item.to} to={item.to}>
              <span className="nav-icon">{item.icon}</span>
              {item.label}
            </NavLink>
            ))}
        </nav>
        <div className="sidebar-footer">CHIQUISTRUKIS · MVP</div>
      </aside>
      <div className="main">
        <header className="header">
          <div className="header-left">{title ?? "Dashboard"}</div>
          <div className="header-right">
            <div className="user-info">
              <div className="user-avatar">{session.username.slice(0, 2).toUpperCase()}</div>
              <div className="user-meta">
                <div>{session.username}</div>
                <div className="role">{session.role}</div>
              </div>
            </div>
            <button
              className="btn btn-sm btn-ghost"
              disabled={loggingOut}
              type="button"
              onClick={logout}
            >
              {loggingOut && <span className="btn-spinner" />}
              {loggingOut ? "Saliendo" : "Salir"}
            </button>
          </div>
        </header>
        <main className="content">
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/personal" element={modulePage(session, "personal", <StaffPage />)} />
            <Route path="/carga" element={modulePage(session, "asistencia_biometrica", <ImportPage />)} />
            <Route path="/asistencia" element={modulePage(session, "administracion_asistencia", <AttendancePage />)} />
            <Route path="/justificaciones" element={modulePage(session, "administracion_asistencia", <JustificationsPage />)} />
            <Route path="/reportes" element={modulePage(session, "reportes_oficiales", <ReportsPage />)} />
          </Routes>
        </main>
      </div>
    </div>
  );
}

function DashboardPage() {
  const today = new Date();
  const [month, setMonth] = useState(today.getMonth() + 1);
  const [year, setYear] = useState(today.getFullYear());
  const [data, setData] = useState<DashboardIndicators | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    apiClient
      .get<DashboardIndicators>("/api/v1/dashboard/indicators", {
        params: { month, year },
      })
      .then((response) => setData(response.data))
      .catch(() => setError("No se pudo cargar el dashboard"));
  }, [month, year]);

  const distribution = data?.mark_distribution ?? {};
  const maxValue = Math.max(1, ...Object.values(distribution));

  return (
    <>
      <PageHeader
        title="Resumen operativo"
        description="Indicadores del sistema y distribución de marcaciones del período"
      />
      <Filters
        month={month}
        onMonthChange={setMonth}
        onYearChange={setYear}
        year={year}
      />
      {error && <div className="alert-danger">{error}</div>}
      <div className="kpi-grid compact">
        <KpiCard
          accent="blue"
          label="Archivos cargados"
          value={data?.total_uploaded_files ?? 0}
          trend="Importaciones biométricas"
        />
        <KpiCard
          accent="green"
          label="Empleados activos"
          value={data?.active_staff_members ?? 0}
          trend="Personal en la institución"
        />
      </div>
      <section className="card">
        <div className="card-header">
          Marcaciones del mes · {monthOptions.find((item) => item.value === month)?.label}{" "}
          {year}
        </div>
        <div className="card-body">
          <div className="chart-bars">
            {statusLabels.map((item) => (
              <div className="chart-bar-wrap" key={item.key}>
                <span className="chart-bar-value">{distribution[item.key] ?? 0}</span>
                <div
                  className={`chart-bar ${item.className}`}
                  style={{
                    height: `${Math.max(
                      8,
                      ((distribution[item.key] ?? 0) / maxValue) * 100,
                    )}%`,
                  }}
                />
                <span className="chart-bar-label">{item.label}</span>
              </div>
            ))}
          </div>
        </div>
      </section>
      <section className="card">
        <div className="card-header">Últimas cargas</div>
        <DataTable
          columns={["Archivo", "Período", "Estado", "Filas"]}
          rows={(data?.recent_imports ?? []).map((item) => [
            item.file_name,
            `${item.period_start ?? "-"} / ${item.period_end ?? "-"}`,
            statusText(item.status),
            String(item.total_rows),
          ])}
          emptyText="Sin cargas registradas"
        />
      </section>
    </>
  );
}

function StaffPage() {
  const [staffMembers, setStaffMembers] = useState<StaffMember[]>(
    () => staffMembersCache ?? [],
  );
  const [loading, setLoading] = useState(staffMembersCache === null);
  const [editingStaff, setEditingStaff] = useState<StaffMember | null>(null);
  const [confirmation, setConfirmation] = useState<{
    action: "save" | "toggle-status";
    staff: StaffMember;
  } | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | "Y" | "N">("Y");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    let cancelled = false;
    loadStaffMembers()
      .then((rows) => {
        if (!cancelled) setStaffMembers(rows);
      })
      .catch(() => {
        if (!cancelled) {
          setStaffMembers([]);
          setError("No se pudo cargar el personal.");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const visibleStaff = staffMembers.filter((item) => {
    const query = search.trim().toLowerCase();
    const matchesSearch = !query || [item.dni, item.last_names, item.first_names, item.job_title]
      .some((value) => value.toLowerCase().includes(query));
    return matchesSearch && (statusFilter === "all" || item.is_active === statusFilter);
  });

  const saveStaff = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!editingStaff) return;
    setConfirmation({ action: "save", staff: editingStaff });
  };

  const persistStaff = async (staff: StaffMember, successMessage: string) => {
    setSaving(true);
    setError("");
    try {
      const response = staff.id === 0
        ? await apiClient.post<StaffMember>("/api/v1/staff-members", staff)
        : await apiClient.put<StaffMember>(`/api/v1/staff-members/${staff.id}`, staff);
      setStaffMembers((current) =>
        staff.id === 0
          ? [response.data, ...current]
          : current.map((item) => item.id === response.data.id ? response.data : item),
      );
      if (staffMembersCache) {
        staffMembersCache = staff.id === 0
          ? [response.data, ...staffMembersCache]
          : staffMembersCache.map((item) =>
              item.id === response.data.id ? response.data : item,
            );
      }
      setEditingStaff(null);
      setMessage(successMessage);
    } catch {
      setError("No se pudieron guardar los cambios. Verifica los datos e inténtalo nuevamente.");
    } finally {
      setSaving(false);
    }
  };

  const confirmAction = async () => {
    if (!confirmation) return;
    const { action, staff } = confirmation;
    setConfirmation(null);
    if (action === "save") {
      await persistStaff(
        staff,
        staff.id === 0
          ? "Personal registrado correctamente."
          : "Datos del personal actualizados correctamente.",
      );
      return;
    }
    const nextStatus = staff.is_active === "Y" ? "N" : "Y";
    await persistStaff(
      { ...staff, is_active: nextStatus },
      nextStatus === "Y" ? "Personal activado correctamente." : "Personal desactivado correctamente.",
    );
  };

  const updateEditingStaff = (field: keyof StaffMember, value: string) => {
    setEditingStaff((current) => current ? { ...current, [field]: value } : current);
  };

  return (
    <>
      <PageHeader
        title="Personal"
        description="Docentes y auxiliares registrados en la institución educativa"
      />
      <div className="filters staff-filters">
        <label className="form-field grow">
          <span>Buscar</span>
          <input
            onChange={(event) => setSearch(event.target.value)}
            placeholder="DNI, nombres o apellidos"
            value={search}
          />
        </label>
        <label className="form-field">
          <span>Estado</span>
          <select onChange={(event) => setStatusFilter(event.target.value as "all" | "Y" | "N")} value={statusFilter}>
            <option value="all">Todos</option>
            <option value="Y">Activos</option>
            <option value="N">Inactivos</option>
          </select>
        </label>
        <div className="filter-actions">
          <button
            className="btn btn-primary"
            onClick={() => setEditingStaff({
              id: 0,
              dni: "",
              last_names: "",
              first_names: "",
              job_title: "Docente",
              employment_status: "",
              is_active: "Y",
            })}
            type="button"
          >
            Nuevo personal
          </button>
        </div>
      </div>
      {message && <div className="alert-success">{message}</div>}
      {error && <div className="alert-danger">{error}</div>}
      <section className="card">
        <div className="card-header">Personal registrado</div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>DNI</th>
                <th>Apellidos y nombres</th>
                <th>Cargo</th>
                <th>Condición</th>
                <th>Estado</th>
                <th aria-label="Acciones" />
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={6} className="empty-cell">Cargando...</td></tr>
              ) : visibleStaff.length ? visibleStaff.map((item) => (
                <tr key={item.id}>
                  <td>{item.dni}</td>
                  <td>{item.last_names}, {item.first_names}</td>
                  <td>{item.job_title}</td>
                  <td>{item.employment_status ?? "-"}</td>
                  <td>
                    <button
                      className={`badge status-button ${item.is_active === "Y" ? "badge-success" : "badge-muted"}`}
                      onClick={() => { setConfirmation({ action: "toggle-status", staff: item }); setError(""); setMessage(""); }}
                      title={item.is_active === "Y" ? "Desactivar personal" : "Activar personal"}
                      type="button"
                    >
                      {item.is_active === "Y" ? "Activo" : "Inactivo"}
                    </button>
                  </td>
                  <td className="staff-actions">
                    <button
                      className="btn btn-sm btn-secondary"
                      onClick={() => { setEditingStaff({ ...item }); setError(""); setMessage(""); }}
                      type="button"
                    >
                      Editar
                    </button>
                  </td>
                </tr>
              )) : (
                <tr><td colSpan={6} className="empty-cell">Sin personal registrado</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
      {editingStaff && (
        <div className="modal-backdrop" role="presentation">
          <section aria-labelledby="edit-staff-title" aria-modal="true" className="modal-card" role="dialog">
            <div className="modal-header">
              <div>
                <h2 id="edit-staff-title">{editingStaff.id === 0 ? "Nuevo personal" : "Editar personal"}</h2>
                <p>{editingStaff.id === 0 ? "Registra un docente o auxiliar." : "Actualiza los datos del registro seleccionado."}</p>
              </div>
              <button aria-label="Cerrar" className="modal-close" onClick={() => setEditingStaff(null)} type="button">×</button>
            </div>
            <form onSubmit={saveStaff}>
              <div className="modal-body form-grid staff-form-grid">
                <label className="form-field">
                  <span>DNI</span>
                  <input inputMode="numeric" maxLength={8} onChange={(event) => updateEditingStaff("dni", event.target.value)} pattern="[0-9]{8}" required value={editingStaff.dni} />
                </label>
                <label className="form-field">
                  <span>Cargo</span>
                  <input onChange={(event) => updateEditingStaff("job_title", event.target.value)} required value={editingStaff.job_title} />
                </label>
                <label className="form-field">
                  <span>Apellidos</span>
                  <input onChange={(event) => updateEditingStaff("last_names", event.target.value)} required value={editingStaff.last_names} />
                </label>
                <label className="form-field">
                  <span>Nombres</span>
                  <input onChange={(event) => updateEditingStaff("first_names", event.target.value)} required value={editingStaff.first_names} />
                </label>
                <label className="form-field">
                  <span>Condición</span>
                  <input onChange={(event) => updateEditingStaff("employment_status", event.target.value)} value={editingStaff.employment_status ?? ""} />
                </label>
              </div>
              <div className="modal-footer">
                <button className="btn btn-secondary" disabled={saving} onClick={() => setEditingStaff(null)} type="button">Cancelar</button>
                <button className="btn btn-primary" disabled={saving} type="submit">{saving ? "Guardando..." : editingStaff.id === 0 ? "Registrar personal" : "Guardar cambios"}</button>
              </div>
            </form>
          </section>
        </div>
      )}
      {confirmation && (
        <div className="modal-backdrop confirmation-backdrop" role="presentation">
          <section aria-labelledby="confirmation-title" aria-modal="true" className="confirmation-card" role="dialog">
            <div className="confirmation-icon">!</div>
            <h2 id="confirmation-title">
              {confirmation.action === "save"
                ? confirmation.staff.id === 0 ? "¿Registrar personal?" : "¿Guardar cambios?"
                : confirmation.staff.is_active === "Y" ? "¿Desactivar personal?" : "¿Activar personal?"}
            </h2>
            <p>
              {confirmation.action === "save"
                ? confirmation.staff.id === 0
                  ? `Se registrará a ${confirmation.staff.last_names}, ${confirmation.staff.first_names}.`
                  : `Se actualizarán los datos de ${confirmation.staff.last_names}, ${confirmation.staff.first_names}.`
                : `${confirmation.staff.last_names}, ${confirmation.staff.first_names} quedará ${confirmation.staff.is_active === "Y" ? "inactivo" : "activo"}.`}
            </p>
            <div className="confirmation-actions">
              <button className="btn btn-secondary" disabled={saving} onClick={() => setConfirmation(null)} type="button">Cancelar</button>
              <button className="btn btn-primary" disabled={saving} onClick={confirmAction} type="button">
                {saving ? "Guardando..." : "Sí, continuar"}
              </button>
            </div>
          </section>
        </div>
      )}
    </>
  );
}

function ImportPage() {
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [currentImport, setCurrentImport] = useState<BiometricImport | null>(null);
  const [imports, setImports] = useState<BiometricImport[]>([]);
  const [rowDrafts, setRowDrafts] = useState<Record<number, ImportRowDraft>>({});
  const [loading, setLoading] = useState(false);
  const [importsLoading, setImportsLoading] = useState(true);
  const [importsLoaded, setImportsLoaded] = useState(false);
  const [importAction, setImportAction] = useState("");
  const [rowLoadingId, setRowLoadingId] = useState<number | null>(null);
  const [processingLabel, setProcessingLabel] = useState("");
  const [wizardView, setWizardView] = useState<"file" | "review" | "confirm">("file");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!message) return undefined;
    const timeoutId = window.setTimeout(() => setMessage(""), 2400);
    return () => window.clearTimeout(timeoutId);
  }, [message]);

  const syncRowDrafts = (rows: ImportRow[] = []) => {
    setRowDrafts(
      Object.fromEntries(
        rows.map((row) => [
          row.row_id,
          {
            dni: row.dni,
            last_names: row.last_names,
            first_names: row.first_names,
          },
        ]),
      ),
    );
  };

  useEffect(() => {
    let cancelled = false;
    apiClient
      .get<BiometricImport[]>("/api/v1/biometric-imports", {
        params: { limit: 10 },
      })
      .then((response) => {
        if (!cancelled) {
          setImports(response.data);
          setImportsLoaded(true);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setImports([]);
          setImportsLoaded(true);
          setError("No se pudo cargar el historial de cargas.");
        }
      })
      .finally(() => {
        if (!cancelled) setImportsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const loadImports = async () => {
    setImportsLoading(true);
    try {
      const response = await apiClient.get<BiometricImport[]>("/api/v1/biometric-imports", {
        params: { limit: 10 },
      });
      setImports(response.data);
      setImportsLoaded(true);
    } catch {
      setError("No se pudo actualizar el historial de cargas.");
    } finally {
      setImportsLoading(false);
    }
  };

  const handleFileChange = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null;
    setSelectedFile(file);
    setCurrentImport(null);
    setMessage("");
    setError("");
    if (file) {
      await processFile(file);
    }
  };

  const uploadFile = async () => {
    if (!selectedFile) {
      inputRef.current?.click();
      return;
    }
    await processFile(selectedFile);
  };

  const processFile = async (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    setLoading(true);
    setImportAction("process");
    setError("");
    setMessage("");
    setProcessingLabel("Analizando archivo, normalizando formato y validando DNI");

    try {
      const response = await apiClient.post<BiometricImport>(
        "/api/v1/biometric-imports",
        formData,
      );
      setCurrentImport(response.data);
      setWizardView("review");
      syncRowDrafts(response.data.rows ?? []);
      setImports((current) => [
        response.data,
        ...current.filter((item) => item.id !== response.data.id),
      ]);
      setMessage("Archivo cargado como borrador");
    } catch {
      setError("No se pudo subir el archivo. Verifica formato y sesión.");
    } finally {
      setLoading(false);
      setImportAction("");
      setProcessingLabel("");
    }
  };

  const confirmImport = async () => {
    if (!currentImport) return;
    setLoading(true);
    setImportAction("confirm");
    setProcessingLabel("Confirmando carga y consolidando asistencia");
    setError("");
    setMessage("");
    try {
      await apiClient.post<BiometricImport>(
        `/api/v1/biometric-imports/${currentImport.id}/confirmation`,
      );
      setImports((current) =>
        current.map((item) =>
          item.id === currentImport.id ? { ...item, status: "confirmed" } : item,
        ),
      );
      navigate(
        `/asistencia?import_id=${currentImport.id}&file=${encodeURIComponent(
          currentImport.file_name,
        )}&month=${currentImport.period_start?.slice(5, 7) ?? ""}&year=${
          currentImport.period_start?.slice(0, 4) ?? ""
        }`,
      );
    } catch {
      setError("No se pudo confirmar la carga.");
    } finally {
      setLoading(false);
      setImportAction("");
      setProcessingLabel("");
    }
  };

  const cancelImport = async () => {
    if (!currentImport) return;
    setLoading(true);
    setImportAction("cancel");
    setProcessingLabel("Anulando carga");
    setError("");
    setMessage("");
    try {
      const response = await apiClient.post<BiometricImport>(
        `/api/v1/biometric-imports/${currentImport.id}/cancellation`,
        { reason: "Archivo/mes incorrecto" },
      );
      setCurrentImport(null);
      setSelectedFile(null);
      setRowDrafts({});
      setWizardView("file");
      setImports((current) =>
        current.some((item) => item.id === response.data.id)
          ? current.map((item) =>
              item.id === response.data.id ? response.data : item,
            )
          : [response.data, ...current],
      );
      void loadImports();
      setMessage("Carga anulada");
    } catch {
      setError("No se pudo anular la carga.");
    } finally {
      setLoading(false);
      setImportAction("");
      setProcessingLabel("");
    }
  };

  const patchRow = async (row: ImportRow, action: string) => {
    if (!currentImport) return;
    const draft = rowDrafts[row.row_id] ?? {
      dni: row.dni,
      last_names: row.last_names,
      first_names: row.first_names,
    };
    setRowLoadingId(row.row_id);
    setError("");
    setMessage("");
    try {
      const response = await apiClient.patch<ImportRow>(
        `/api/v1/biometric-imports/${currentImport.id}/rows/${row.row_id}`,
        {
          action,
          dni: draft.dni,
          last_names: draft.last_names,
          first_names: draft.first_names,
        },
      );
      const updatedRow = response.data;
      setCurrentImport((current) => {
        if (!current?.rows) return current;
        const rows = current.rows.map((item) =>
          item.row_id === updatedRow.row_id ? updatedRow : item,
        );
        const matchedRows = rows.filter((item) => item.match === "matched").length;
        const newRows = rows.filter(
          (item) => item.match === "new" && !item.resolved && !item.skipped,
        ).length;
        return {
          ...current,
          rows,
          matched_rows: matchedRows,
          new_rows: newRows,
        };
      });
      syncRowDrafts(
        (currentImport.rows ?? []).map((item) =>
          item.row_id === updatedRow.row_id ? updatedRow : item,
        ),
      );
      setMessage("Fila actualizada");
    } catch {
      setError("No se pudo actualizar la fila.");
    } finally {
      setRowLoadingId(null);
    }
  };

  const updateRowDraft = (
    rowId: number,
    field: keyof ImportRowDraft,
    value: string,
  ) => {
    setRowDrafts((current) => ({
      ...current,
      [rowId]: {
        dni: current[rowId]?.dni ?? "",
        last_names: current[rowId]?.last_names ?? "",
        first_names: current[rowId]?.first_names ?? "",
        [field]: value,
      },
    }));
  };

  const step = currentImport?.status === "confirmed"
    ? 4
    : wizardView === "confirm"
      ? 3
      : currentImport
        ? 2
        : 1;

  const canContinueReview = currentImport?.status === "draft";

  return (
    <>
      <PageHeader
        title="Carga biométrica"
        description="Archivo, validación de DNI, período detectado y confirmación"
      />
      <div className="wizard-steps">
        {["Archivo", "Validación", "Confirmación", "Asistencia"].map(
          (label, index) => (
            <div
              className={`wizard-step ${step >= index + 1 ? "active" : ""}`}
              key={label}
            >
              <span>{index + 1}</span>
              {label}
            </div>
          ),
        )}
      </div>
      {loading && (
        <div className="progress-panel">
          <div className="progress-header">
            <strong>Paso {step}: procesando</strong>
            <span>{processingLabel || "Trabajando"}</span>
          </div>
          <div className="progress-track">
            <div className="progress-bar" />
          </div>
        </div>
      )}
      {message && <div className="alert-success">{message}</div>}
      {error && <div className="alert-danger">{error}</div>}
      {step === 1 && (
      <section className="card">
        <div className="card-header">Nueva carga</div>
        <div className="card-body">
          <label className="dropzone" htmlFor="biometric-file">
            <strong className="file-name-text">
              {selectedFile ? selectedFile.name : "Seleccionar archivo"}
            </strong>
            <span>CSV o BAT de simulación biométrica</span>
            <input
              ref={inputRef}
              accept=".csv,.bat,.cmd,text/csv,text/plain"
              id="biometric-file"
              onChange={handleFileChange}
              type="file"
            />
          </label>
          <div className="actions">
            <button
              className="btn btn-primary"
              disabled={loading}
              onClick={uploadFile}
              type="button"
            >
              {importAction === "process" && <span className="btn-spinner" />}
              {importAction === "process"
                ? "Procesando"
                : selectedFile
                  ? "Procesar otra vez"
                  : "Seleccionar archivo"}
            </button>
          </div>
        </div>
      </section>
      )}
      {currentImport && step === 2 && (
        <section className="card">
          <div className="card-header">
            <span>Borrador #{currentImport.id} · {statusText(currentImport.status)}</span>
            <button
              className="btn btn-primary btn-sm"
              disabled={!canContinueReview || loading || rowLoadingId !== null}
              onClick={() => setWizardView("confirm")}
              type="button"
            >
              Siguiente
            </button>
          </div>
          <div className="card-body import-summary">
            <KpiCard
              label="Período"
              value={`${currentImport.period_start ?? "-"} / ${
                currentImport.period_end ?? "-"
              }`}
              trend={currentImport.file_name}
            />
            <KpiCard
              accent="green"
              label="Encontradas"
              value={currentImport.matched_rows}
              trend="Filas verdes"
            />
            <KpiCard
              accent="blue"
              label="Nuevas"
              value={currentImport.new_rows}
              trend="Filas rojas"
            />
          </div>
          <ImportRowsTable
            disabled={currentImport.status !== "draft"}
            onPatchRow={patchRow}
            rowLoadingId={rowLoadingId}
            rowDrafts={rowDrafts}
            rows={currentImport.rows ?? []}
            onUpdateDraft={updateRowDraft}
          />
        </section>
      )}
      {currentImport && step === 3 && (
        <section className="card">
          <div className="card-header">Confirmación</div>
          <div className="card-body import-summary">
            <KpiCard
              label="Archivo"
              value={currentImport.file_name}
              trend={
                currentImport.normalization_source === "openai"
                  ? `Borrador #${currentImport.id} · IA $${currentImport.ai_estimated_cost_usd ?? "0"}`
                  : `Borrador #${currentImport.id}`
              }
              valueClassName="file-name-text"
            />
            <KpiCard
              label="Período"
              value={`${currentImport.period_start ?? "-"} / ${
                currentImport.period_end ?? "-"
              }`}
              trend={`${currentImport.total_rows} filas`}
            />
            <KpiCard
              accent="green"
              label="Encontradas"
              value={currentImport.matched_rows}
              trend="Listas para consolidar"
            />
          </div>
          <div className="card-body actions">
            <button
              className="btn btn-secondary"
              disabled={loading}
              onClick={() => setWizardView("review")}
              type="button"
            >
              Volver
            </button>
            <button
              className="btn btn-primary"
              disabled={loading || currentImport.status !== "draft"}
              onClick={confirmImport}
              type="button"
            >
              {importAction === "confirm" && <span className="btn-spinner" />}
              {importAction === "confirm" ? "Confirmando" : "Finalizar carga"}
            </button>
            <button
              className="btn btn-danger-outline"
              disabled={loading}
              onClick={cancelImport}
              type="button"
            >
              {importAction === "cancel" && <span className="btn-spinner" />}
              {importAction === "cancel" ? "Anulando" : "Anular carga"}
            </button>
          </div>
        </section>
      )}
      {step === 1 && (
      <section className="card">
        <div className="card-header">
          Historial de cargas
          {importsLoading && <span className="subtle-inline">Cargando</span>}
          {!importsLoading && importsLoaded && (
            <span className="subtle-inline">{imports.length} registros</span>
          )}
        </div>
        <DataTable
          columns={["Archivo", "Período", "Estado", "Filas"]}
          rows={imports.map((item) => [
            item.file_name,
            `${item.period_start ?? "-"} / ${item.period_end ?? "-"}`,
            statusText(item.status),
            String(item.total_rows),
          ])}
          emptyText={
            importsLoading ? "Cargando historial..." : "Sin cargas registradas"
          }
        />
      </section>
      )}
    </>
  );
}

function ImportRowsTable({
  rows,
  disabled,
  rowLoadingId,
  rowDrafts,
  onPatchRow,
  onUpdateDraft,
}: {
  rows: ImportRow[];
  disabled: boolean;
  rowLoadingId: number | null;
  rowDrafts: Record<number, ImportRowDraft>;
  onPatchRow: (row: ImportRow, action: string) => void;
  onUpdateDraft: (
    rowId: number,
    field: keyof ImportRowDraft,
    value: string,
  ) => void;
}) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>DNI</th>
            <th>Apellidos y nombres</th>
            <th>Fecha/hora</th>
            <th>Tipo</th>
            <th>Estado</th>
            <th>Acción</th>
          </tr>
        </thead>
        <tbody>
          {rows.length ? (
            rows.map((row) => {
              const isResolved = row.match === "matched" || row.resolved || row.skipped;
              const isEditable = row.match === "new" && !row.skipped && !disabled;
              const draft = rowDrafts[row.row_id] ?? {
                dni: row.dni,
                last_names: row.last_names,
                first_names: row.first_names,
              };
              return (
                <tr
                  className={isResolved ? "row-ok" : "row-warning"}
                  key={row.row_id}
                >
                  <td>{row.order}</td>
                  <td>
                    {isEditable ? (
                      <input
                        className="table-input dni"
                        maxLength={8}
                        onChange={(event) =>
                          onUpdateDraft(row.row_id, "dni", event.target.value)
                        }
                        value={draft.dni}
                      />
                    ) : (
                      row.dni
                    )}
                  </td>
                  <td>
                    {isEditable ? (
                      <div className="inline-edit-grid">
                        <input
                          className="table-input"
                          onChange={(event) =>
                            onUpdateDraft(
                              row.row_id,
                              "last_names",
                              event.target.value,
                            )
                          }
                          placeholder="Apellidos"
                          value={draft.last_names}
                        />
                        <input
                          className="table-input"
                          onChange={(event) =>
                            onUpdateDraft(
                              row.row_id,
                              "first_names",
                              event.target.value,
                            )
                          }
                          placeholder="Nombres"
                          value={draft.first_names}
                        />
                      </div>
                    ) : (
                      `${row.last_names}, ${row.first_names}`
                    )}
                  </td>
                  <td>{row.marked_at ?? "-"}</td>
                  <td>{markTypeText(row.mark_type ?? "")}</td>
                  <td>
                    {row.skipped
                      ? "Omitido"
                      : row.match === "matched"
                        ? "Encontrado"
                        : "Nuevo"}
                  </td>
                  <td>
                    {isEditable ? (
                      <div className="row-actions">
                        <button
                          className="btn btn-sm btn-primary"
                          disabled={rowLoadingId === row.row_id}
                          onClick={() => onPatchRow(row, "research")}
                          type="button"
                        >
                          {rowLoadingId === row.row_id && <span className="btn-spinner" />}
                          {rowLoadingId === row.row_id ? "Buscando" : "Rebuscar"}
                        </button>
                        <button
                          className="btn btn-sm btn-secondary"
                          disabled={rowLoadingId === row.row_id}
                          onClick={() => onPatchRow(row, "register_new")}
                          type="button"
                        >
                          Registrar
                        </button>
                        <button
                          className="btn btn-sm btn-ghost"
                          disabled={rowLoadingId === row.row_id}
                          onClick={() => onPatchRow(row, "skip")}
                          type="button"
                        >
                          Omitir
                        </button>
                      </div>
                    ) : (
                      "-"
                    )}
                  </td>
                </tr>
              );
            })
          ) : (
            <tr>
              <td colSpan={7}>Sin filas para mostrar</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

function AttendancePage() {
  const location = useLocation();
  const query = new URLSearchParams(location.search);
  const importId = query.get("import_id");
  const fileName = query.get("file");
  const today = new Date();
  const initialMonth = Number(query.get("month") || today.getMonth() + 1);
  const initialYear = Number(query.get("year") || today.getFullYear());
  const [month, setMonth] = useState(initialMonth);
  const [year, setYear] = useState(initialYear);
  const [loadedMonth, setLoadedMonth] = useState(initialMonth);
  const [loadedYear, setLoadedYear] = useState(initialYear);
  const [selectedImportId, setSelectedImportId] = useState(
    importId ? Number(importId) : 0,
  );
  const [allImports, setAllImports] = useState<BiometricImport[]>([]);
  const [monthImports, setMonthImports] = useState<BiometricImport[]>([]);
  const [attendanceRows, setAttendanceRows] = useState<AttendanceDay[]>([]);
  const [staffMembers, setStaffMembers] = useState<StaffMember[]>([]);
  const [selectedDay, setSelectedDay] = useState<AttendanceDay | null>(null);
  const [selectedStatus, setSelectedStatus] = useState("present");
  const [lateMinutes, setLateMinutes] = useState(0);
  const [loading, setLoading] = useState(true);
  const [savingDay, setSavingDay] = useState(false);
  const [lockedDayKey, setLockedDayKey] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const loadAttendance = async (
    nextMonth = month,
    nextYear = year,
    nextImportId = selectedImportId,
  ) => {
    setLoading(true);
    setError("");
    try {
      const [attendanceResponse, staffResponse] = await Promise.all([
        apiClient.get<AttendanceDay[]>("/api/v1/attendance-records", {
          params: {
            month: nextMonth,
            year: nextYear,
            import_id: nextImportId || undefined,
          },
        }),
        apiClient.get<StaffMember[]>("/api/v1/staff-members", {
          params: { is_active: "Y" },
        }),
      ]);
      setAttendanceRows(attendanceResponse.data);
      setStaffMembers(staffResponse.data);
      setLoadedMonth(nextMonth);
      setLoadedYear(nextYear);
      setSelectedDay(null);
      setSelectedStatus("present");
      setLateMinutes(0);
      setLockedDayKey("");
    } catch {
      setError("No se pudo cargar la asistencia.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      apiClient.get<BiometricImport[]>("/api/v1/biometric-imports"),
      apiClient.get<StaffMember[]>("/api/v1/staff-members", {
        params: { is_active: "Y" },
      }),
    ])
      .then(async ([importsResponse, staffResponse]) => {
        if (cancelled) return;
        const imports = sortAttendanceImports(
          importsResponse.data.filter((item) => item.status === "confirmed"),
        );
        const selectedPeriod = periodFromImports(
          imports,
          initialMonth,
          initialYear,
          importId ? Number(importId) : undefined,
        );
        const importsForMonth = imports.filter((item) =>
          importTouchesPeriod(item, selectedPeriod.month, selectedPeriod.year),
        );
        const nextImportId =
          importId && imports.some((item) => item.id === Number(importId))
            ? Number(importId)
            : 0;

        setAllImports(imports);
        setMonth(selectedPeriod.month);
        setYear(selectedPeriod.year);
        setMonthImports(importsForMonth);
        setSelectedImportId(nextImportId);
        setStaffMembers(staffResponse.data);
        const attendanceResponse = await apiClient.get<AttendanceDay[]>(
          "/api/v1/attendance-records",
          {
            params: {
              month: selectedPeriod.month,
              year: selectedPeriod.year,
              import_id: nextImportId || undefined,
            },
          },
        );
        if (cancelled) return;
        setAttendanceRows(attendanceResponse.data);
        setLoadedMonth(selectedPeriod.month);
        setLoadedYear(selectedPeriod.year);
        setSelectedDay(null);
        setSelectedStatus("present");
        setLateMinutes(0);
        setLockedDayKey("");
      })
      .catch(() => {
        if (!cancelled) setError("No se pudo cargar la asistencia.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [importId, initialMonth, initialYear]);

  const loadMonthImports = (nextMonth: number, nextYear: number) => {
    const importsForMonth = allImports.filter((item) =>
      importTouchesPeriod(item, nextMonth, nextYear),
    );
    const nextImportId = selectedImportId === 0 || importsForMonth.some((item) => item.id === selectedImportId)
      ? selectedImportId
      : importsForMonth[0]?.id ?? 0;
    setMonthImports(importsForMonth);
    setSelectedImportId(nextImportId);
  };

  const selectImport = (nextImportId: number) => {
    setSelectedImportId(nextImportId);
  };

  const applyAttendanceFilters = async () => {
    const importsForMonth = allImports.filter((item) =>
      importTouchesPeriod(item, month, year),
    );
    const nextImportId = selectedImportId === 0 || importsForMonth.some((item) => item.id === selectedImportId)
      ? selectedImportId
      : importsForMonth[0]?.id ?? 0;
    setMonthImports(importsForMonth);
    setSelectedImportId(nextImportId);
    await loadAttendance(month, year, nextImportId);
  };

  const selectDay = (row: AttendanceDay) => {
    setSelectedDay(row);
    setSelectedStatus(row.status);
    setLateMinutes(row.late_minutes);
    setLockedDayKey("");
    setMessage("");
    setError("");
  };

  const saveDay = async () => {
    if (!selectedDay) return;
    const dayKey = `${selectedDay.staff_member_id}-${selectedDay.attendance_date}`;
    setSavingDay(true);
    setError("");
    setMessage("");
    try {
      const response = await apiClient.put<AttendanceDay>(
        "/api/v1/attendance-records/days",
        {
          staff_member_id: selectedDay.staff_member_id,
          biometric_import_id:
            selectedDay.biometric_import_id ?? (selectedImportId || null),
          attendance_date: selectedDay.attendance_date,
          status: selectedStatus,
          late_minutes: lateMinutes,
          justification_id: selectedDay.justification_id,
        },
      );
      setAttendanceRows((rows) =>
        rows.map((row) =>
          sameAttendanceKey(row, response.data, selectedImportId)
            ? response.data
            : row,
        ),
      );
      setSelectedDay(response.data);
      setLockedDayKey(dayKey);
      setMessage("Día actualizado");
    } catch {
      setError("No se pudo guardar el día.");
    } finally {
      setSavingDay(false);
    }
  };

  const staffById = Object.fromEntries(staffMembers.map((staff) => [staff.id, staff]));
  const selectedStaff = selectedDay ? staffById[selectedDay.staff_member_id] : null;
  const selectedDayKey = selectedDay
    ? `${selectedDay.staff_member_id}-${selectedDay.attendance_date}`
    : "";
  const fieldsLocked = !selectedDay || savingDay || lockedDayKey === selectedDayKey;
  const availableYears = yearsFromImports(allImports, year);
  const availableMonths = monthsFromImports(allImports, year, month);
  const noMonthFiles = !loading && monthImports.length === 0;

  return (
    <>
      <PageHeader
        title="Asistencia"
        description="Grilla mensual y panel diario de edición"
      />
      {importId && (
        <div className="context-banner">
          <strong>Carga confirmada #{importId}</strong>
          <span>
            {fileName ?? "Archivo biométrico"} · Período{" "}
            {month && year ? `${String(month).padStart(2, "0")}/${year}` : "detectado"}
          </span>
        </div>
      )}
      <div className="filters">
        <label className="form-field">
          <span>Mes</span>
          <select
            onChange={(event) => {
              const nextMonth = Number(event.target.value);
              setMonth(nextMonth);
              loadMonthImports(nextMonth, year);
            }}
            value={month}
          >
            {availableMonths.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
        <label className="form-field">
          <span>Año</span>
          <select
            onChange={(event) => {
              const nextYear = Number(event.target.value);
              const nextMonth = monthsFromImports(allImports, nextYear, month)[0].value;
              setYear(nextYear);
              setMonth(nextMonth);
              loadMonthImports(nextMonth, nextYear);
            }}
            value={year}
          >
            {availableYears.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
        <label className="form-field grow">
          <span>Archivo</span>
          <select
            disabled={!monthImports.length}
            onChange={(event) => selectImport(Number(event.target.value))}
            value={selectedImportId}
          >
            <option value="0">
              {monthImports.length
                ? "Todos los archivos del mes"
                : "Sin archivos para este mes"}
            </option>
            {monthImports.map((item) => (
              <option key={item.id} value={item.id}>
                #{item.id} · {item.file_name} · {statusText(item.status)}
              </option>
            ))}
          </select>
        </label>
        <div className="filter-actions">
          <button
            className="btn btn-sm btn-primary"
            disabled={loading || !monthImports.length}
            onClick={applyAttendanceFilters}
            type="button"
          >
            {loading && <span className="btn-spinner" />}
            {loading ? "Filtrando" : "Filtrar"}
          </button>
        </div>
      </div>
      {message && <div className="attendance-toast">{message}</div>}
      {noMonthFiles && (
        <div className="alert-info">No hay archivos disponibles para este mes.</div>
      )}
      {error && !noMonthFiles && <div className="alert-danger">{error}</div>}
      <div className="attendance-layout">
        <section className="card attendance-grid">
          <div className="card-header">
            Asistencia cargada · {String(loadedMonth).padStart(2, "0")}/{loadedYear}
          </div>
          <AttendanceMonthGrid
            month={loadedMonth}
            onSelect={selectDay}
            rows={attendanceRows}
            selectedDayKey={selectedDayKey}
            staffById={staffById}
            year={loadedYear}
          />
        </section>
        <section className="card attendance-panel">
          <div className="card-header">Editar</div>
          <div className="card-body panel-stack">
            <div className="edit-summary">
              <div>
                <span>Personal</span>
                <strong>
                  {selectedStaff
                    ? `${selectedStaff.last_names}, ${selectedStaff.first_names}`
                    : selectedDay
                      ? `ID ${selectedDay.staff_member_id}`
                      : "Seleccione una celda"}
                </strong>
              </div>
              <div className="edit-summary-grid">
                <div>
                  <span>DNI</span>
                  <strong>{selectedStaff?.dni ?? "-"}</strong>
                </div>
                <div>
                  <span>Fecha</span>
                  <strong>{selectedDay?.attendance_date ?? "-"}</strong>
                </div>
              </div>
            </div>
            <label className="form-field">
              <span>Estado</span>
              <select
                disabled={fieldsLocked}
                onChange={(event) => setSelectedStatus(event.target.value)}
                value={selectedStatus}
              >
                {attendanceStatuses.map((status) => (
                  <option key={status.value} value={status.value}>
                    {status.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="form-field">
              <span>Minutos tardanza</span>
              <input
                disabled={fieldsLocked}
                min="0"
                onChange={(event) => setLateMinutes(Number(event.target.value))}
                type="number"
                value={lateMinutes}
              />
            </label>
            <button
              className="btn btn-secondary"
              disabled={!selectedDay || savingDay || lockedDayKey === selectedDayKey}
              onClick={saveDay}
              type="button"
            >
              {savingDay && <span className="btn-spinner" />}
              {savingDay
                ? "Guardando"
                : lockedDayKey === selectedDayKey
                  ? "Guardado"
                  : "Guardar"}
            </button>
          </div>
        </section>
      </div>
    </>
  );
}

function formatJustificationPeriod(startDate: string, endDate: string) {
  const format = (value: string) => {
    const [year, month, day] = value.split("-");
    return `${day}/${month}/${year}`;
  };
  return startDate === endDate
    ? format(startDate)
    : `${format(startDate)} al ${format(endDate)}`;
}

function JustificationsPage() {
  const today = new Date();
  const localDate = new Date(today.getTime() - today.getTimezoneOffset() * 60_000)
    .toISOString()
    .slice(0, 10);
  const initialMonth = today.getMonth() + 1;
  const initialYear = today.getFullYear();
  const [staffMembers, setStaffMembers] = useState<StaffMember[]>([]);
  const [justifications, setJustifications] = useState<Justification[]>([]);
  const [absences, setAbsences] = useState<AttendanceDay[]>([]);
  const [absenceMonth, setAbsenceMonth] = useState(initialMonth);
  const [absenceYear, setAbsenceYear] = useState(initialYear);
  const [loadedAbsenceMonth, setLoadedAbsenceMonth] = useState(initialMonth);
  const [loadedAbsenceYear, setLoadedAbsenceYear] = useState(initialYear);
  const [absencesLoading, setAbsencesLoading] = useState(true);
  const [staffMemberId, setStaffMemberId] = useState(0);
  const [startDate, setStartDate] = useState(localDate);
  const [endDate, setEndDate] = useState(localDate);
  const [normCode, setNormCode] = useState("LG");
  const [reason, setReason] = useState("");
  const [supportFile, setSupportFile] = useState<File | null>(null);
  const [fileInputKey, setFileInputKey] = useState(0);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [downloadingId, setDownloadingId] = useState<number | null>(null);
  const [itemToCancel, setItemToCancel] = useState<Justification | null>(null);
  const [cancelReason, setCancelReason] = useState("");
  const [cancelling, setCancelling] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    let active = true;
    Promise.all([
      loadStaffMembers(),
      apiClient.get<Justification[]>("/api/v1/justifications"),
      apiClient.get<AttendanceDay[]>("/api/v1/attendance-records", {
        params: { month: initialMonth, year: initialYear },
      }),
    ])
      .then(([staff, response, attendanceResponse]) => {
        if (!active) return;
        setStaffMembers(staff);
        setJustifications(response.data);
        setAbsences(
          attendanceResponse.data.filter(
            (item) => item.status === "absent" && item.justification_id === null,
          ),
        );
      })
      .catch(() => {
        if (active) setError("No se pudieron cargar las justificaciones.");
      })
      .finally(() => {
        if (active) {
          setLoading(false);
          setAbsencesLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, [initialMonth, initialYear]);

  const activeStaffMembers = staffMembers.filter((item) => item.is_active === "Y");
  const staffById = new Map(staffMembers.map((item) => [item.id, item]));
  const selectedAbsences = absences.filter(
    (item) =>
      item.staff_member_id === staffMemberId &&
      item.attendance_date >= startDate &&
      item.attendance_date <= endDate,
  );
  const absenceYears = Array.from({ length: 7 }, (_, index) => initialYear + 1 - index);

  const loadAbsences = async (month = absenceMonth, year = absenceYear) => {
    setAbsencesLoading(true);
    setError("");
    try {
      const response = await apiClient.get<AttendanceDay[]>(
        "/api/v1/attendance-records",
        { params: { month, year } },
      );
      setAbsences(
        response.data.filter(
          (item) => item.status === "absent" && item.justification_id === null,
        ),
      );
      setLoadedAbsenceMonth(month);
      setLoadedAbsenceYear(year);
    } catch {
      setAbsences([]);
      setError("No se pudieron cargar las inasistencias pendientes.");
    } finally {
      setAbsencesLoading(false);
    }
  };

  const selectAbsence = (item: AttendanceDay) => {
    setStaffMemberId(item.staff_member_id);
    setStartDate(item.attendance_date);
    setEndDate(item.attendance_date);
    setError("");
    setMessage("");
  };

  const changeNorm = (event: ChangeEvent<HTMLSelectElement>) => {
    setNormCode(event.target.value);
  };

  const changeSupportFile = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null;
    setError("");
    if (file && file.size > 5 * 1024 * 1024) {
      setSupportFile(null);
      setFileInputKey((current) => current + 1);
      setError("El sustento no puede superar los 5 MB.");
      return;
    }
    setSupportFile(file);
  };

  const submitJustification = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    setMessage("");
    if (!staffMemberId) {
      setError("Selecciona una inasistencia pendiente.");
      return;
    }
    if (endDate < startDate) {
      setError("La fecha fin no puede ser anterior a la fecha inicio.");
      return;
    }
    if (!reason.trim()) {
      setError("Ingresa el motivo o detalle de la justificación.");
      return;
    }
    if (selectedAbsences.length === 0) {
      setError("El periodo seleccionado no contiene inasistencias pendientes.");
      return;
    }

    const formData = new FormData();
    formData.append("staff_member_id", String(staffMemberId));
    formData.append("start_date", startDate);
    formData.append("end_date", endDate);
    formData.append("norm_code", normCode);
    formData.append("with_pay", normCode === "LG" ? "Y" : "N");
    formData.append("reason", reason.trim());
    if (supportFile) formData.append("support_file", supportFile);

    setSubmitting(true);
    try {
      const response = await apiClient.post<Justification>(
        "/api/v1/justifications",
        formData,
      );
      setJustifications((current) => [
        response.data,
        ...current.filter((item) => item.id !== response.data.id),
      ]);
      setReason("");
      setSupportFile(null);
      setFileInputKey((current) => current + 1);
      setStaffMemberId(0);
      setMessage("La justificación se registró correctamente.");
      await loadAbsences(loadedAbsenceMonth, loadedAbsenceYear);
    } catch {
      setError(
        "No se pudo registrar la justificación. Revisa los datos y el sustento.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  const downloadSupport = async (item: Justification) => {
    setDownloadingId(item.id);
    setError("");
    try {
      const response = await apiClient.get(
        `/api/v1/justifications/${item.id}/support`,
        { responseType: "blob" },
      );
      const storedName = item.support_file_path?.split(/[\\/]/).pop() ?? "sustento";
      const downloadName = storedName.includes("_")
        ? storedName.slice(storedName.indexOf("_") + 1)
        : storedName;
      const url = URL.createObjectURL(response.data as Blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = downloadName;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1_000);
    } catch {
      setError("No se pudo descargar el sustento solicitado.");
    } finally {
      setDownloadingId(null);
    }
  };

  const cancelJustification = async () => {
    if (!itemToCancel || !cancelReason.trim()) {
      setError("Indica el motivo de la anulación.");
      return;
    }
    setCancelling(true);
    setError("");
    setMessage("");
    try {
      const response = await apiClient.post<Justification>(
        `/api/v1/justifications/${itemToCancel.id}/cancellation`,
        { reason: cancelReason.trim() },
      );
      setJustifications((current) =>
        current.map((item) => (item.id === response.data.id ? response.data : item)),
      );
      setItemToCancel(null);
      setCancelReason("");
      setMessage("La justificación fue anulada correctamente.");
      await loadAbsences(loadedAbsenceMonth, loadedAbsenceYear);
    } catch {
      setError("No se pudo anular la justificación.");
    } finally {
      setCancelling(false);
    }
  };

  return (
    <>
      <PageHeader
        title="Justificaciones y Permisos"
        description="Gestión de licencias con/sin goce y adjunto de sustentos"
      />
      <section className="card">
        <div className="card-header">
          <span>Inasistencias pendientes por justificar</span>
          <span className="subtle-inline">
            {monthOptions.find((item) => item.value === loadedAbsenceMonth)?.label}{" "}
            {loadedAbsenceYear} · {absences.length} registros
          </span>
        </div>
        <div className="card-body">
          <form
            className="filters"
            onSubmit={(event) => {
              event.preventDefault();
              void loadAbsences();
            }}
          >
            <label className="form-field">
              <span>Mes</span>
              <select
                onChange={(event) => setAbsenceMonth(Number(event.target.value))}
                value={absenceMonth}
              >
                {monthOptions.map((item) => (
                  <option key={item.value} value={item.value}>{item.label}</option>
                ))}
              </select>
            </label>
            <label className="form-field">
              <span>Año</span>
              <select
                onChange={(event) => setAbsenceYear(Number(event.target.value))}
                value={absenceYear}
              >
                {absenceYears.map((year) => (
                  <option key={year} value={year}>{year}</option>
                ))}
              </select>
            </label>
            <button className="btn btn-primary" disabled={absencesLoading} type="submit">
              {absencesLoading ? "Cargando" : "Buscar inasistencias"}
            </button>
          </form>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Fecha</th>
                <th>Personal</th>
                <th>DNI</th>
                <th>Origen</th>
                <th>Estado</th>
                <th>Acción</th>
              </tr>
            </thead>
            <tbody>
              {absencesLoading && (
                <tr><td className="empty-cell" colSpan={6}>Cargando...</td></tr>
              )}
              {!absencesLoading && absences.length === 0 && (
                <tr>
                  <td className="empty-cell" colSpan={6}>
                    No hay inasistencias pendientes en el periodo seleccionado.
                  </td>
                </tr>
              )}
              {!absencesLoading && absences.map((item) => {
                const staff = staffById.get(item.staff_member_id);
                const selected = selectedAbsences.some((absence) => absence.id === item.id);
                return (
                  <tr key={item.id}>
                    <td>{formatJustificationPeriod(item.attendance_date, item.attendance_date)}</td>
                    <td>
                      <strong>
                        {staff
                          ? `${staff.last_names}, ${staff.first_names}`
                          : `Personal #${item.staff_member_id}`}
                      </strong>
                    </td>
                    <td>{staff?.dni ?? "—"}</td>
                    <td>
                      {item.biometric_import_id
                        ? `Carga biométrica #${item.biometric_import_id}`
                        : "Registro manual"}
                    </td>
                    <td><span className="badge badge-warning">Inasistencia</span></td>
                    <td>
                      <button
                        className={`btn btn-sm ${selected ? "btn-primary" : "btn-secondary"}`}
                        onClick={() => selectAbsence(item)}
                        type="button"
                      >
                        {selected ? "Seleccionada" : "Justificar"}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>
      <section className="card">
        <div className="card-header">Nueva Justificación</div>
        <form className="card-body justification-form" onSubmit={submitJustification}>
          {error && <div className="alert-danger justification-alert">{error}</div>}
          {message && <div className="alert-success justification-alert">{message}</div>}
          <div className="justification-form-grid">
            <label className="form-field">
              <span>Personal Docente / Auxiliar</span>
              <select
                disabled
                required
                value={staffMemberId}
              >
                {loading && <option value={0}>Cargando...</option>}
                {!loading && staffMemberId === 0 && activeStaffMembers.length > 0 && (
                  <option value={0}>Selecciona una inasistencia pendiente</option>
                )}
                {!loading && activeStaffMembers.length === 0 && (
                  <option value={0}>No hay personal activo</option>
                )}
                {activeStaffMembers.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.dni} - {item.last_names}, {item.first_names}
                  </option>
                ))}
              </select>
            </label>
            <label className="form-field">
              <span>Fecha Inicio</span>
              <input
                disabled={!staffMemberId}
                max={endDate}
                onChange={(event) => setStartDate(event.target.value)}
                required
                type="date"
                value={startDate}
              />
            </label>
            <label className="form-field">
              <span>Fecha Fin</span>
              <input
                disabled={!staffMemberId}
                min={startDate}
                onChange={(event) => setEndDate(event.target.value)}
                required
                type="date"
                value={endDate}
              />
            </label>
            <label className="form-field">
              <span>Código Norma RSG N.° 326</span>
              <select onChange={changeNorm} value={normCode}>
                {justificationNorms.map((item) => (
                  <option key={item.code} value={item.code}>
                    {item.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="form-field full-width">
              <span>Motivo / Detalle</span>
              <input
                maxLength={500}
                onChange={(event) => setReason(event.target.value)}
                placeholder="Descripción del motivo de la licencia..."
                required
                value={reason}
              />
            </label>
            <div className="form-field full-width">
              <span>Sustento Adjunto (PDF/Imagen, máximo 5 MB)</span>
              <label className="file-upload-control">
                <input
                  accept=".pdf,.jpg,.jpeg,.png,.webp,application/pdf,image/jpeg,image/png,image/webp"
                  className="file-upload-input"
                  key={fileInputKey}
                  onChange={changeSupportFile}
                  type="file"
                />
                <span className="file-upload-button">
                  <span aria-hidden="true" className="file-upload-icon">↑</span>
                  Seleccionar archivo
                </span>
                <span className={`file-upload-name ${supportFile ? "has-file" : ""}`}>
                  {supportFile ? supportFile.name : "Ningún archivo seleccionado"}
                </span>
              </label>
              <small className="file-caption">Formatos permitidos: PDF, JPG, PNG o WEBP.</small>
            </div>
          </div>
          <p className="subtle-inline">
            {selectedAbsences.length > 0
              ? `${selectedAbsences.length} inasistencia(s) pendiente(s) incluida(s) en el periodo.`
              : "Selecciona una inasistencia de la tabla para habilitar el registro."}
          </p>
          <div className="justification-actions">
            <button
              className="btn btn-primary"
              disabled={loading || submitting || selectedAbsences.length === 0}
              type="submit"
            >
              {submitting && <span className="btn-spinner" />}
              {submitting ? "Registrando" : "Registrar Justificación"}
            </button>
          </div>
        </form>
      </section>

      <section className="card">
        <div className="card-header">
          <span>Justificaciones registradas</span>
          <span className="subtle-inline">{justifications.length} registros</span>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Personal</th>
                <th>Periodo</th>
                <th>Norma</th>
                <th>Goce</th>
                <th>Motivo</th>
                <th>Sustento</th>
                <th>Estado</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr>
                  <td className="empty-cell" colSpan={8}>Cargando...</td>
                </tr>
              )}
              {!loading && justifications.length === 0 && (
                <tr>
                  <td className="empty-cell" colSpan={8}>
                    No hay justificaciones registradas.
                  </td>
                </tr>
              )}
              {!loading &&
                justifications.map((item) => {
                  const staff = staffById.get(item.staff_member_id);
                  const norm = justificationNorms.find(
                    (option) => option.code === item.norm_code,
                  );
                  return (
                    <tr key={item.id}>
                      <td>
                        <strong>{staff ? `${staff.last_names}, ${staff.first_names}` : `Personal #${item.staff_member_id}`}</strong>
                        {staff && <small className="table-subtext">DNI {staff.dni}</small>}
                      </td>
                      <td>{formatJustificationPeriod(item.start_date, item.end_date)}</td>
                      <td title={norm?.label}>{item.norm_code}</td>
                      <td>{item.with_pay === "Y" ? "Sí" : "No"}</td>
                      <td className="justification-reason">{item.reason || "—"}</td>
                      <td>
                        {item.support_file_path ? (
                          <button
                            className="btn btn-secondary btn-sm"
                            disabled={downloadingId === item.id}
                            onClick={() => downloadSupport(item)}
                            type="button"
                          >
                            {downloadingId === item.id ? "Descargando" : "Ver sustento"}
                          </button>
                        ) : (
                          <span className="subtle-inline">Sin adjunto</span>
                        )}
                      </td>
                      <td>
                        <span
                          className={`badge ${item.status === "active" ? "badge-success" : "badge-muted"}`}
                        >
                          {item.status === "active" ? "Activa" : "Anulada"}
                        </span>
                      </td>
                      <td>
                        {item.status === "active" && (
                          <button
                            className="btn btn-danger-outline btn-sm"
                            onClick={() => {
                              setItemToCancel(item);
                              setCancelReason("");
                              setError("");
                            }}
                            type="button"
                          >
                            Anular
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
            </tbody>
          </table>
        </div>
      </section>

      {itemToCancel && (
        <div className="modal-backdrop confirmation-backdrop" role="presentation">
          <div aria-modal="true" className="confirmation-card" role="dialog">
            <div className="confirmation-icon">!</div>
            <h2>Anular justificación</h2>
            <p>
              Esta acción revertirá la justificación aplicada a la asistencia del
              periodo seleccionado.
            </p>
            <label className="form-field cancellation-reason">
              <span>Motivo de anulación</span>
              <input
                autoFocus
                maxLength={250}
                onChange={(event) => setCancelReason(event.target.value)}
                placeholder="Indica por qué se anula..."
                value={cancelReason}
              />
            </label>
            <div className="confirmation-actions">
              <button
                className="btn btn-secondary"
                disabled={cancelling}
                onClick={() => setItemToCancel(null)}
                type="button"
              >
                Volver
              </button>
              <button
                className="btn btn-danger-outline"
                disabled={cancelling || !cancelReason.trim()}
                onClick={cancelJustification}
                type="button"
              >
                {cancelling ? "Anulando" : "Confirmar anulación"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function ReportsPage() {
  const today = new Date();
  const [month, setMonth] = useState(today.getMonth() + 1);
  const [year, setYear] = useState(today.getFullYear());
  const [monthImports, setMonthImports] = useState<BiometricImport[]>([]);
  const [selectedImportId, setSelectedImportId] = useState(0);
  const [annex, setAnnex] = useState<"03" | "04">("03");
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState("");
  const [preview, setPreview] = useState<ReportPreview | null>(null);
  const [showHeaderEdit, setShowHeaderEdit] = useState(false);

  const [header, setHeader] = useState({
    ugel: "SAN ROMAN",
    school_name: "IE Demo CHIQUISTRUKIS",
    modular_code: "1234567",
    education_level: "Secundaria",
    shift_name: "Manana",
    address: "Direccion de IE",
    department: "PUNO",
    province: "SAN ROMAN",
    district: "",
  });

  const monthNames = [
    "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Setiembre", "Octubre", "Noviembre", "Diciembre",
  ];

  const updateHeader = (key: string, value: string) =>
    setHeader((prev) => ({ ...prev, [key]: value }));

  const syncHeader = (institution: Annex03Report["institution"]) => {
    setHeader((current) => ({
      ...current,
      ugel: institution.ugel ?? current.ugel,
      school_name: institution.school_name ?? current.school_name,
      modular_code: institution.modular_code ?? current.modular_code,
      education_level: institution.education_level ?? current.education_level,
      shift_name: institution.shift_name ?? current.shift_name,
    }));
  };

  useEffect(() => {
    let cancelled = false;
    apiClient
      .get<BiometricImport[]>("/api/v1/biometric-imports", {
        params: { status: "confirmed", month, year },
      })
      .then((response) => {
        if (cancelled) return;
        setMonthImports(response.data);
        setSelectedImportId(0);
      })
      .catch(() => {
        if (cancelled) return;
        setError("No se pudieron cargar los archivos de asistencia.");
        setMonthImports([]);
        setSelectedImportId(0);
      });
    return () => {
      cancelled = true;
    };
  }, [month, year]);

  // Carga automática al cambiar mes / año / anexo
  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      setError("");
      try {
        const params = {
          month,
          year,
          format: "json",
          import_id: selectedImportId || undefined,
        } as const;
        if (cancelled) return;
        if (annex === "03") {
          const response = await apiClient.get<Annex03Report>(
            "/api/v1/reports/annex-03",
            { params },
          );
          if (cancelled) return;
          const data = response.data;
          syncHeader(data.institution);
          setPreview({
            type: "03",
            rows: (data.rows || []).map((row) => ({
              dni: row.dni || "",
              full_name: row.full_name || "",
              days: row.days || [],
            })),
          });
        } else {
          const response = await apiClient.get<Annex04Report>(
            "/api/v1/reports/annex-04",
            { params },
          );
          if (cancelled) return;
          const data = response.data;
          syncHeader(data.institution);
          setPreview({
            type: "04",
            totals: data.totals || {},
            staff_count: data.staff_count ?? 0,
          });
        }
      } catch {
        if (!cancelled) {
          setError("No se pudo cargar la vista previa");
          setPreview(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    void load();
    return () => {
      cancelled = true;
    };
  }, [month, year, annex, selectedImportId]);

  const exportExcel = async () => {
    setExporting(true);
    setError("");
    try {
      const response = await apiClient.get("/api/v1/reports/monthly-export", {
        params: {
          month,
          year,
          import_id: selectedImportId || undefined,
          ugel: header.ugel,
          school_name: header.school_name,
          modular_code: header.modular_code,
          education_level: header.education_level,
          shift_name: header.shift_name,
          address: header.address,
          department: header.department,
          province: header.province,
          district: header.district,
        },
        responseType: "blob",
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute(
        "download",
        `asistencia_${year}_${String(month).padStart(2, "0")}.xlsx`,
      );
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      setError("No se pudo exportar el Excel");
    } finally {
      setExporting(false);
    }
  };

  const daysInMonth = new Date(year, month, 0).getDate();
  const allDays = Array.from({ length: daysInMonth }, (_, i) => i + 1);
  const statusLetter = (status: string) =>
    ({ present: "A", late: "T", absent: "F", justified: "J", leave: "L", permission: "P" }[
      status
    ] || "");

  return (
    <>
      <PageHeader
        title="Reportes oficiales"
        description="Anexo 03 y 04 · vista previa automática · exportar Excel listo para imprimir"
      />
      {/* Barra superior: filtros + exportar */}
      <div className="report-toolbar">
        <div className="report-toolbar-content">
          <label className="form-field">
            <span>Anexo</span>
            <select value={annex} onChange={(e) => setAnnex(e.target.value as "03" | "04")}>
              <option value="03">Anexo 03 – Detallado</option>
              <option value="04">Anexo 04 – Consolidado</option>
            </select>
          </label>
          <label className="form-field">
            <span>Mes</span>
            <select value={month} onChange={(e) => setMonth(Number(e.target.value))}>
              {monthNames.slice(1).map((name, idx) => (
                <option key={name} value={idx + 1}>{name}</option>
              ))}
            </select>
          </label>
          <label className="form-field">
            <span>Año</span>
            <select value={year} onChange={(e) => setYear(Number(e.target.value))}>
              {Array.from({ length: 7 }, (_, index) => today.getFullYear() + 1 - index).map(
                (item) => <option key={item} value={item}>{item}</option>,
              )}
            </select>
          </label>
          <label className="form-field">
            <span>Archivo</span>
            <select
              disabled={!monthImports.length}
              onChange={(event) => setSelectedImportId(Number(event.target.value))}
              value={selectedImportId}
            >
              <option value={0}>
                {monthImports.length
                  ? "Todos los archivos del mes"
                  : "Sin archivos para este mes"}
              </option>
              {monthImports.map((item) => (
                <option key={item.id} value={item.id}>
                  #{item.id} · {item.file_name}
                </option>
              ))}
            </select>
          </label>
          <div className="report-actions">
            <button
              className="btn btn-sm btn-ghost"
              type="button"
              onClick={() => setShowHeaderEdit((v) => !v)}
            >
              {showHeaderEdit ? "Ocultar cabecera" : "Editar cabecera"}
            </button>
            <button
              className="btn btn-sm btn-primary"
              type="button"
              disabled={exporting}
              onClick={exportExcel}
            >
              {exporting ? "Exportando…" : "Exportar Excel"}
            </button>
          </div>
        </div>

        {/* Panel colapsable de cabecera (no son campos de BD: solo override al exportar) */}
        {showHeaderEdit && (
          <div className="report-header-edit">
            <p className="report-header-hint">
              Estos datos se usan solo en el Excel exportado. No modifican la base de datos.
              Vienen precargados de la institución activa.
            </p>
            <div className="report-header-grid">
              {(
                [
                  ["ugel", "UGEL"],
                  ["school_name", "Institucion educativa"],
                  ["modular_code", "Codigo modular"],
                  ["education_level", "Nivel / modalidad"],
                  ["shift_name", "Turno"],
                  ["address", "Lugar / direccion"],
                  ["department", "Departamento"],
                  ["province", "Provincia"],
                  ["district", "Distrito"],
                ] as const
              ).map(([key, label]) => (
                <label className="form-field" key={key}>
                  <span>{label}</span>
                  <input
                    value={header[key]}
                    onChange={(e) => updateHeader(key, e.target.value)}
                  />
                </label>
              ))}
            </div>
          </div>
        )}
      </div>

      {error && <div className="alert-danger">{error}</div>}
      {loading && <p className="text-muted">Cargando vista previa…</p>}

      {/* Vista previa estilo oficial */}
      <section className="card report-preview">
        <div className="card-header">
          Vista previa · Anexo {annex} · {monthNames[month]} {year}
        </div>
        <div className="card-body">
          <div className="annex-official">
            <div className="annex-legal">
              NORMAS PARA EL REGISTRO Y CONTROL DE ASISTENCIA Y SU APLICACION EN LA
              PLANILLA UNICA DE PAGOS (R.S.G. N 326-2017-MINEDU)
            </div>
            <div className="annex-title-bar">
              {annex === "03"
                ? "FORMATO 01: REPORTE DE ASISTENCIA DETALLADO"
                : "FORMATO 02: REPORTE CONSOLIDADO DE INASISTENCIAS, TARDANZAS Y PERMISOS"}
            </div>
            <div className="annex-meta">
              <div><strong>UGEL:</strong> {header.ugel || "—"}</div>
              <div><strong>MES:</strong> <span className="text-red">{monthNames[month].toUpperCase()}</span></div>
              <div><strong>ANO:</strong> <span className="text-red">{year}</span></div>
              <div><strong>TURNO:</strong> <span className="text-red">{header.shift_name || "—"}</span></div>
            </div>
            <div className="annex-meta">
              <div><strong>IE:</strong> <span className="text-red">{header.school_name || "—"}</span></div>
              <div><strong>COD. MOD:</strong> <span className="text-red">{header.modular_code || "—"}</span></div>
              <div><strong>NIVEL:</strong> <span className="text-red">{header.education_level || "—"}</span></div>
              <div><strong>DEP/PROV/DIS:</strong> {header.department} / {header.province} / {header.district || "—"}</div>
            </div>

            {preview?.type === "03" && (
              <div className="table-wrap annex-table annex-calendar" style={{ marginTop: 12 }}>
                <table>
                  <thead>
                    <tr>
                      <th>N°</th>
                      <th>DNI</th>
                      <th>Apellidos y nombres</th>
                      {allDays.map((d) => (
                        <th key={d} className="day-col">{d}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {(preview.rows || []).length === 0 ? (
                      <tr>
                        <td colSpan={allDays.length + 3}>Sin registros del mes</td>
                      </tr>
                    ) : (
                      preview.rows.map((row, idx) => {
                        const byDate: Record<string, string> = {};
                        row.days.forEach((day) => {
                          byDate[day.attendance_date] = statusLetter(day.status);
                        });
                        return (
                          <tr key={`${row.dni}-${idx}`}>
                            <td>{idx + 1}</td>
                            <td>{row.dni}</td>
                            <td style={{ textAlign: "left", whiteSpace: "nowrap" }}>
                              {row.full_name}
                            </td>
                            {allDays.map((d) => {
                              const key = `${year}-${String(month).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
                              return (
                                <td key={d} className="day-col">
                                  {byDate[key] || ""}
                                </td>
                              );
                            })}
                          </tr>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>
            )}

            {preview?.type === "04" && (
              <div className="table-wrap annex-table" style={{ marginTop: 12 }}>
                <table>
                  <thead>
                    <tr>
                      <th>Presentes</th>
                      <th>Tardanzas</th>
                      <th>Faltas</th>
                      <th>Justificadas</th>
                      <th>Licencias</th>
                      <th>Permisos</th>
                      <th>Personal</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>{preview.totals?.present ?? 0}</td>
                      <td>{preview.totals?.late ?? 0}</td>
                      <td>{preview.totals?.absent ?? 0}</td>
                      <td>{preview.totals?.justified ?? 0}</td>
                      <td>{preview.totals?.leave ?? 0}</td>
                      <td>{preview.totals?.permission ?? 0}</td>
                      <td>{preview.staff_count ?? 0}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </section>
    </>
  );
}

function PageHeader({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="page-header">
      <h1 className="page-title">{title}</h1>
      <p className="page-desc">{description}</p>
    </div>
  );
}

function Filters({
  month,
  year,
  onMonthChange,
  onYearChange,
  showSearch = false,
  vertical = false,
}: {
  month: number;
  year: number;
  onMonthChange: (month: number) => void;
  onYearChange: (year: number) => void;
  showSearch?: boolean;
  vertical?: boolean;
}) {
  return (
    <div className={vertical ? "filters vertical" : "filters"}>
      {showSearch && (
        <label className="form-field grow">
          <span>Buscar</span>
          <input placeholder="DNI o apellidos" />
        </label>
      )}
      <label className="form-field">
        <span>Mes</span>
        <select value={month} onChange={(event) => onMonthChange(Number(event.target.value))}>
          {monthOptions.map((item) => (
            <option key={item.value} value={item.value}>{item.label}</option>
          ))}
        </select>
      </label>
      <label className="form-field">
        <span>Año</span>
        <select value={year} onChange={(event) => onYearChange(Number(event.target.value))}>
          {Array.from({ length: 7 }, (_, index) => new Date().getFullYear() + 1 - index).map(
            (item) => <option key={item} value={item}>{item}</option>,
          )}
        </select>
      </label>
    </div>
  );
}

function KpiCard({
  label,
  value,
  trend,
  accent = "",
  valueClassName = "",
}: {
  label: string;
  value: string | number;
  trend: string;
  accent?: string;
  valueClassName?: string;
}) {
  return (
    <div className={`kpi-card ${accent}`}>
      <div className="label">{label}</div>
      <div className={`value ${valueClassName}`}>{value}</div>
      <div className="trend">{trend}</div>
    </div>
  );
}

function DataTable({
  columns,
  rows,
  emptyText = "Sin registros",
}: {
  columns: string[];
  rows: string[][];
  emptyText?: string;
}) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column}>{column}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length ? (
            rows.map((row) => (
              <tr key={row.join("|")}>
                {row.map((cell, index) => (
                  <td key={`${cell}-${index}`}>{cell}</td>
                ))}
              </tr>
            ))
          ) : (
            <tr>
              <td colSpan={columns.length}>{emptyText}</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

function AttendanceMonthGrid({
  rows,
  staffById,
  month,
  year,
  selectedDayKey,
  onSelect,
}: {
  rows: AttendanceDay[];
  staffById: Record<number, StaffMember>;
  month: number;
  year: number;
  selectedDayKey: string;
  onSelect: (row: AttendanceDay) => void;
}) {
  const days = Array.from(
    { length: new Date(year, month, 0).getDate() },
    (_, index) => index + 1,
  );
  const rowsByStaff = rows.reduce<Record<number, Record<number, AttendanceDay>>>(
    (acc, row) => {
      const day = Number(row.attendance_date.slice(8, 10));
      acc[row.staff_member_id] = acc[row.staff_member_id] ?? {};
      acc[row.staff_member_id][day] = row;
      return acc;
    },
    {},
  );
  const staffIds = Object.keys(rowsByStaff).map(Number);

  return (
    <div className="table-wrap attendance-month-wrap">
      <table className="attendance-month-table">
        <thead>
          <tr>
            <th className="sticky-name sticky-head">Personal</th>
            {days.map((day) => (
              <th key={day}>{String(day).padStart(2, "0")}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {staffIds.length ? (
            staffIds.map((staffId) => {
              const staff = staffById[staffId];
              return (
                <tr key={staffId}>
                  <td className="sticky-name">
                    {staff
                      ? `${staff.last_names}, ${staff.first_names}`
                      : `ID ${staffId}`}
                  </td>
                  {days.map((day) => {
                    const row = rowsByStaff[staffId]?.[day];
                    return (
                      <td key={day}>
                        {row ? (
                          <button
                            className={`day-cell ${row.status} ${
                              selectedDayKey ===
                              `${row.staff_member_id}-${row.attendance_date}`
                                ? "selected"
                                : ""
                            }`}
                            onClick={() => onSelect(row)}
                            type="button"
                          >
                            {attendanceStatusShort(row.status)}
                          </button>
                        ) : (
                          <span className="day-empty">-</span>
                        )}
                      </td>
                    );
                  })}
                </tr>
              );
            })
          ) : (
            <tr>
              <td colSpan={days.length + 1}>Sin asistencia para este archivo</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

const statusLabels = [
  { key: "present", label: "Asistencia", className: "success" },
  { key: "late", label: "Tardanza", className: "warning" },
  { key: "absent", label: "Inasistencia", className: "danger" },
  { key: "justified", label: "Justificado", className: "info" },
  { key: "leave", label: "Licencia", className: "violet" },
  { key: "permission", label: "Permiso", className: "muted" },
];

const attendanceStatuses = [
  { value: "present", label: "Asistencia" },
  { value: "late", label: "Tardanza" },
  { value: "absent", label: "Inasistencia" },
  { value: "justified", label: "Justificado" },
  { value: "leave", label: "Licencia" },
  { value: "permission", label: "Permiso" },
];

const monthOptions = [
  { value: 1, label: "Enero" },
  { value: 2, label: "Febrero" },
  { value: 3, label: "Marzo" },
  { value: 4, label: "Abril" },
  { value: 5, label: "Mayo" },
  { value: 6, label: "Junio" },
  { value: 7, label: "Julio" },
  { value: 8, label: "Agosto" },
  { value: 9, label: "Septiembre" },
  { value: 10, label: "Octubre" },
  { value: 11, label: "Noviembre" },
  { value: 12, label: "Diciembre" },
];

function statusText(status: string) {
  const labels: Record<string, string> = {
    draft: "Borrador",
    confirmed: "Confirmada",
    cancelled: "Anulada",
  };
  return labels[status] ?? status;
}

function sortAttendanceImports(imports: BiometricImport[]) {
  const weight: Record<BiometricImport["status"], number> = {
    confirmed: 0,
    draft: 1,
    cancelled: 2,
  };
  return [...imports].sort(
    (left, right) => weight[left.status] - weight[right.status] || right.id - left.id,
  );
}

function periodFromImports(
  imports: BiometricImport[],
  fallbackMonth: number,
  fallbackYear: number,
  preferredImportId?: number,
) {
  const firstImport =
    imports.find(
      (item) =>
        item.id === preferredImportId && (item.period_start || item.period_end),
    ) ?? imports.find((item) => item.period_start || item.period_end);
  const period = firstImport?.period_start ?? firstImport?.period_end;
  if (!period) return { month: fallbackMonth, year: fallbackYear };
  return {
    month: Number(period.slice(5, 7)),
    year: Number(period.slice(0, 4)),
  };
}

function sameAttendanceKey(
  left: AttendanceDay,
  right: AttendanceDay,
  selectedImportId: number,
) {
  const leftImportId = (left.biometric_import_id ?? selectedImportId) || null;
  const rightImportId = (right.biometric_import_id ?? selectedImportId) || null;
  return (
    left.staff_member_id === right.staff_member_id &&
    left.attendance_date === right.attendance_date &&
    leftImportId === rightImportId
  );
}

function markTypeText(markType: string) {
  const labels: Record<string, string> = {
    entry: "Entrada",
    exit: "Salida",
  };
  return labels[markType] ?? markType;
}

function attendanceStatusShort(status: string) {
  const labels: Record<string, string> = {
    present: "A",
    late: "T",
    absent: "F",
    justified: "J",
    leave: "L",
    permission: "P",
  };
  return labels[status] ?? status.slice(0, 1).toUpperCase();
}

export default App;
