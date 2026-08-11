import { ChangeEvent, FormEvent, useEffect, useRef, useState } from "react";
import {
  Navigate,
  NavLink,
  Route,
  Routes,
  useLocation,
  useNavigate,
} from "react-router-dom";

import apiClient from "./services/apiClient";

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

const STORAGE_KEY = "chiquistrukis.session";

const navigationItems = [
  { to: "/dashboard", label: "Dashboard", icon: "D" },
  { to: "/personal", label: "Personal", icon: "P" },
  { to: "/carga", label: "Carga biométrica", icon: "C" },
  { to: "/asistencia", label: "Asistencia", icon: "A" },
  { to: "/justificaciones", label: "Justificaciones", icon: "J" },
  { to: "/reportes", label: "Reportes", icon: "R" },
];

function readStoredSession(): Session | null {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as Session;
  } catch {
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem("token");
    return null;
  }
}

function App() {
  const [session, setSession] = useState<Session | null>(() => readStoredSession());

  const handleSession = (nextSession: Session | null) => {
    setSession(nextSession);
    if (nextSession) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(nextSession));
      localStorage.setItem("token", nextSession.token);
    } else {
      clearStaffMembersCache();
      localStorage.removeItem(STORAGE_KEY);
      localStorage.removeItem("token");
    }
  };

  return (
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
  );
}

function LoginPage({ onLogin }: { onLogin: (session: Session) => void }) {
  const [username, setUsername] = useState("director.demo");
  const [password, setPassword] = useState("");
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
      onLogin(response.data);
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
            <input type="checkbox" defaultChecked /> Recordarme
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
          {navigationItems.map((item) => (
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
            <Route path="/personal" element={<StaffPage />} />
            <Route path="/carga" element={<ImportPage />} />
            <Route path="/asistencia" element={<AttendancePage />} />
            <Route path="/justificaciones" element={<JustificationsPage />} />
            <Route path="/reportes" element={<ReportsPage />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}

function DashboardPage() {
  const [data, setData] = useState<DashboardIndicators | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    apiClient
      .get<DashboardIndicators>("/api/v1/dashboard/indicators", {
        params: { month: 7, year: 2026 },
      })
      .then((response) => setData(response.data))
      .catch(() => setError("No se pudo cargar el dashboard"));
  }, []);

  const distribution = data?.mark_distribution ?? {};
  const maxValue = Math.max(1, ...Object.values(distribution));

  return (
    <>
      <PageHeader
        title="Resumen operativo"
        description="Indicadores del sistema y distribución de marcaciones del período"
      />
      <Filters />
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
        <div className="card-header">Marcaciones del mes · Julio 2026</div>
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
      const response = await apiClient.put<StaffMember>(
        `/api/v1/staff-members/${staff.id}`,
        staff,
      );
      setStaffMembers((current) =>
        current.map((item) => {
          const updated = item.id === response.data.id ? response.data : item;
          return updated;
        }),
      );
      if (staffMembersCache) {
        staffMembersCache = staffMembersCache.map((item) =>
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
      await persistStaff(staff, "Datos del personal actualizados correctamente.");
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
                <h2 id="edit-staff-title">Editar personal</h2>
                <p>Actualiza los datos del registro seleccionado.</p>
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
                <button className="btn btn-primary" disabled={saving} type="submit">{saving ? "Guardando..." : "Guardar cambios"}</button>
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
              {confirmation.action === "save" ? "¿Guardar cambios?" : confirmation.staff.is_active === "Y" ? "¿Desactivar personal?" : "¿Activar personal?"}
            </h2>
            <p>
              {confirmation.action === "save"
                ? `Se actualizarán los datos de ${confirmation.staff.last_names}, ${confirmation.staff.first_names}.`
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
  const [importAction, setImportAction] = useState("");
  const [rowLoadingId, setRowLoadingId] = useState<number | null>(null);
  const [processingLabel, setProcessingLabel] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

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
      .get<BiometricImport[]>("/api/v1/biometric-imports")
      .then((response) => {
        if (!cancelled) setImports(response.data);
      })
      .catch(() => {
        if (!cancelled) setImports([]);
      });
    return () => {
      cancelled = true;
    };
  }, []);

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
    setProcessingLabel("Leyendo archivo y validando DNI");

    try {
      const response = await apiClient.post<BiometricImport>(
        "/api/v1/biometric-imports",
        formData,
      );
      setCurrentImport(response.data);
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
      setCurrentImport(response.data);
      setImports((current) =>
        current.map((item) => (item.id === response.data.id ? response.data : item)),
      );
      setMessage("Carga anulada");
    } catch {
      setError("Solo puedes anular una carga confirmada.");
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

  const unresolvedRows =
    currentImport?.rows?.filter(
      (row) => row.match === "new" && !row.resolved && !row.skipped,
    ).length ?? 0;

  const step = !currentImport
    ? loading
      ? 2
      : 1
    : currentImport.status === "draft" && unresolvedRows > 0
      ? 2
      : currentImport.status === "draft"
        ? 3
        : 4;

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
      <section className="card">
        <div className="card-header">Nueva carga</div>
        <div className="card-body">
          <label className="dropzone" htmlFor="biometric-file">
            <strong>{selectedFile ? selectedFile.name : "Seleccionar archivo"}</strong>
            <span>CSV o BAT de simulación biométrica</span>
            <input
              ref={inputRef}
              accept=".csv,.bat,.cmd,text/csv,text/plain"
              id="biometric-file"
              onChange={handleFileChange}
              type="file"
            />
          </label>
          {message && <div className="alert-success">{message}</div>}
          {error && <div className="alert-danger">{error}</div>}
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
            <button
              className="btn btn-secondary"
              disabled={!currentImport || loading || currentImport.status !== "draft"}
              onClick={confirmImport}
              type="button"
            >
              {importAction === "confirm" && <span className="btn-spinner" />}
              {importAction === "confirm" ? "Confirmando" : "Confirmar carga"}
            </button>
            <button
              className="btn btn-danger-outline"
              disabled={!currentImport || loading}
              onClick={cancelImport}
              type="button"
            >
              {importAction === "cancel" && <span className="btn-spinner" />}
              {importAction === "cancel" ? "Anulando" : "Anular carga"}
            </button>
          </div>
        </div>
      </section>
      {currentImport && (
        <section className="card">
          <div className="card-header">
            Borrador #{currentImport.id} · {statusText(currentImport.status)}
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
      <section className="card">
        <div className="card-header">Historial de cargas</div>
        <DataTable
          columns={["Archivo", "Período", "Estado", "Filas"]}
          rows={imports.map((item) => [
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
  const initialMonth = Number(query.get("month") || 7);
  const initialYear = Number(query.get("year") || 2026);
  const [month, setMonth] = useState(initialMonth);
  const [year, setYear] = useState(initialYear);
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
      setSelectedDay(attendanceResponse.data[0] ?? null);
      setSelectedStatus(attendanceResponse.data[0]?.status ?? "present");
      setLateMinutes(attendanceResponse.data[0]?.late_minutes ?? 0);
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
        const imports = importsResponse.data;
        const selectedPeriod = periodFromImports(imports, initialMonth, initialYear);
        const importsForMonth = imports.filter((item) =>
          importTouchesPeriod(item, selectedPeriod.month, selectedPeriod.year),
        );
        const nextImportId =
          importId && imports.some((item) => item.id === Number(importId))
            ? Number(importId)
            : importsForMonth[0]?.id ?? 0;

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
        setSelectedDay(attendanceResponse.data[0] ?? null);
        setSelectedStatus(attendanceResponse.data[0]?.status ?? "present");
        setLateMinutes(attendanceResponse.data[0]?.late_minutes ?? 0);
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
    const nextImportId = importsForMonth.some((item) => item.id === selectedImportId)
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
    const nextImportId = importsForMonth.some((item) => item.id === selectedImportId)
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
        rows.map((row) => (row.id === response.data.id ? response.data : row)),
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
            onChange={(event) => selectImport(Number(event.target.value))}
            value={selectedImportId}
          >
            <option value="0">Todos los archivos del mes</option>
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
            disabled={loading}
            onClick={applyAttendanceFilters}
            type="button"
          >
            {loading && <span className="btn-spinner" />}
            {loading ? "Filtrando" : "Filtrar"}
          </button>
        </div>
      </div>
      {message && <div className="alert-success">{message}</div>}
      {error && <div className="alert-danger">{error}</div>}
      <div className="attendance-layout">
        <section className="card attendance-grid">
          <div className="card-header">
            Asistencia cargada · {String(month).padStart(2, "0")}/{year}
          </div>
          <AttendanceMonthGrid
            month={month}
            onSelect={selectDay}
            rows={attendanceRows}
            staffById={staffById}
            year={year}
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

function JustificationsPage() {
  return (
    <>
      <PageHeader
        title="Justificaciones"
        description="Licencias, permisos y archivos de sustento"
      />
      <section className="card">
        <div className="card-header">Registro</div>
        <div className="card-body form-grid">
          <label className="form-field">
            <span>DNI</span>
            <input placeholder="45678912" />
          </label>
          <label className="form-field">
            <span>Norma</span>
            <input placeholder="LIC" />
          </label>
          <label className="form-field wide">
            <span>Motivo</span>
            <input placeholder="Licencia aprobada" />
          </label>
          <button className="btn btn-primary" type="button">
            Registrar
          </button>
        </div>
      </section>
    </>
  );
}

function ReportsPage() {
  const [month, setMonth] = useState(7);
  const [year, setYear] = useState(2026);
  const [report, setReport] = useState<Annex03Report | null>(null);
  const [previewSheet, setPreviewSheet] = useState<"attendance" | "consolidated">("attendance");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const generatePreview = async () => {
    setLoading(true);
    setError("");
    try {
      const response = await apiClient.get<Annex03Report>("/api/v1/reports/annex-03", {
        params: { month, year, format: "json" },
      });
      setReport(response.data);
    } catch {
      setError("No se pudo generar la vista previa del reporte.");
    } finally {
      setLoading(false);
    }
  };

  const downloadExcel = async () => {
    setLoading(true);
    setError("");
    try {
      const response = await apiClient.get("/api/v1/reports/monthly-export", {
        params: { month, year },
        responseType: "blob",
      });
      const url = URL.createObjectURL(response.data as Blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `asistencia_${year}_${String(month).padStart(2, "0")}.xlsx`;
      link.click();
      URL.revokeObjectURL(url);
    } catch {
      setError("No se pudo descargar el archivo Excel.");
    } finally {
      setLoading(false);
    }
  };

  const previewRows = (report?.rows ?? []).map((row, index) => {
    const counts = row.days.reduce<Record<string, number>>((result, day) => {
      result[day.status] = (result[day.status] ?? 0) + 1;
      return result;
    }, {});
    const lateMinutes = row.days.reduce(
      (total, day) => total + (day.status === "late" ? day.late_minutes : 0), 0,
    );
    return { ...row, index: index + 1, counts, lateMinutes };
  });

  return (
    <>
      <PageHeader
        title="Reportes"
        description="Exportación mensual de asistencia y reporte consolidado"
      />
      <section className="report-toolbar card">
        <div className="card-body report-toolbar-content">
          <label className="form-field">
            <span>Asistencia</span>
            <select value="monthly" disabled>
              <option value="monthly">Anexo 03 + Anexo 04</option>
            </select>
          </label>
          <label className="form-field">
            <span>Mes</span>
            <select onChange={(event) => setMonth(Number(event.target.value))} value={month}>
              {monthOptions.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
            </select>
          </label>
          <label className="form-field">
            <span>Año</span>
            <select onChange={(event) => setYear(Number(event.target.value))} value={year}>
              <option value="2026">2026</option>
              <option value="2025">2025</option>
            </select>
          </label>
          <label className="form-field">
            <span>Archivo</span>
            <select value="xlsx" disabled><option value="xlsx">Excel (.xlsx)</option></select>
          </label>
          <div className="report-actions">
            <button className="btn btn-secondary" disabled={loading} onClick={generatePreview} type="button">
              {loading ? "Generando..." : "Previsualizar"}
            </button>
            <button className="btn btn-primary" disabled={loading} onClick={downloadExcel} type="button">
              Descargar Excel
            </button>
          </div>
        </div>
      </section>
      {error && <div className="alert-danger">{error}</div>}
      <section className="card report-preview">
        <div className="card-header">
          <span>Vista previa {report ? `· ${monthOptions.find((item) => item.value === month)?.label} ${year}` : ""}</span>
          {report && <span className="report-institution">{report.institution.school_name} · {report.institution.ugel}</span>}
        </div>
        <div className="report-tabs">
          <button className={previewSheet === "attendance" ? "active" : ""} onClick={() => setPreviewSheet("attendance")} type="button">Asistencia · Anexo 03</button>
          <button className={previewSheet === "consolidated" ? "active" : ""} onClick={() => setPreviewSheet("consolidated")} type="button">Reporte consolidado · Anexo 04</button>
        </div>
        {report ? previewSheet === "attendance" ? (
          <DataTable
            columns={["N°", "DNI", "Apellidos y nombres", "Asistencia", "Tardanzas", "Faltas", "Justificados"]}
            rows={previewRows.map((row) => [
              String(row.index), row.dni, row.full_name,
              String(row.counts.present ?? 0), String(row.counts.late ?? 0),
              String(row.counts.absent ?? 0), String(row.counts.justified ?? 0),
            ])}
            emptyText="No hay asistencia registrada para este mes"
          />
        ) : (
          <DataTable
            columns={["N°", "DNI", "Apellidos y nombres", "Inasist. justificadas", "Licencias", "Faltas", "Tardanzas (min.)", "Permisos"]}
            rows={previewRows.map((row) => [
              String(row.index), row.dni, row.full_name,
              String(row.counts.justified ?? 0), String(row.counts.leave ?? 0),
              String(row.counts.absent ?? 0), String(row.lateMinutes), String(row.counts.permission ?? 0),
            ])}
            emptyText="No hay asistencia registrada para este mes"
          />
        ) : <div className="report-empty">Selecciona el período y presiona <strong>Previsualizar</strong>.</div>}
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
  showSearch = false,
  vertical = false,
}: {
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
        <select defaultValue="7">
          <option value="7">Julio</option>
          <option value="6">Junio</option>
          <option value="5">Mayo</option>
        </select>
      </label>
      <label className="form-field">
        <span>Año</span>
        <select defaultValue="2026">
          <option value="2026">2026</option>
        </select>
      </label>
      {!vertical && (
        <div className="filter-actions">
          <button className="btn btn-sm btn-primary" type="button">
            Aplicar
          </button>
        </div>
      )}
    </div>
  );
}

function KpiCard({
  label,
  value,
  trend,
  accent = "",
}: {
  label: string;
  value: string | number;
  trend: string;
  accent?: string;
}) {
  return (
    <div className={`kpi-card ${accent}`}>
      <div className="label">{label}</div>
      <div className="value">{value}</div>
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
  onSelect,
}: {
  rows: AttendanceDay[];
  staffById: Record<number, StaffMember>;
  month: number;
  year: number;
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
            <th>Personal</th>
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
                            className={`day-cell ${row.status}`}
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

function importTouchesPeriod(item: BiometricImport, month: number, year: number) {
  const prefix = `${year}-${String(month).padStart(2, "0")}`;
  return (
    String(item.period_start ?? "").startsWith(prefix) ||
    String(item.period_end ?? "").startsWith(prefix)
  );
}

function periodFromImports(
  imports: BiometricImport[],
  fallbackMonth: number,
  fallbackYear: number,
) {
  const firstImport = imports.find((item) => item.period_start || item.period_end);
  const period = firstImport?.period_start ?? firstImport?.period_end;
  if (!period) return { month: fallbackMonth, year: fallbackYear };
  return {
    month: Number(period.slice(5, 7)),
    year: Number(period.slice(0, 4)),
  };
}

function yearsFromImports(imports: BiometricImport[], fallbackYear: number) {
  const years = new Set<number>();
  imports.forEach((item) => {
    if (item.period_start) years.add(Number(item.period_start.slice(0, 4)));
    if (item.period_end) years.add(Number(item.period_end.slice(0, 4)));
  });
  return years.size ? [...years].sort((a, b) => b - a) : [fallbackYear];
}

function monthsFromImports(
  imports: BiometricImport[],
  selectedYear: number,
  fallbackMonth: number,
) {
  const months = new Set<number>();
  imports.forEach((item) => {
    if (item.period_start?.startsWith(`${selectedYear}-`)) {
      months.add(Number(item.period_start.slice(5, 7)));
    }
    if (item.period_end?.startsWith(`${selectedYear}-`)) {
      months.add(Number(item.period_end.slice(5, 7)));
    }
  });
  const values = months.size ? [...months].sort((a, b) => b - a) : [fallbackMonth];
  return values.map((value) => ({
    value,
    label: monthOptions.find((item) => item.value === value)?.label ?? String(value),
  }));
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
