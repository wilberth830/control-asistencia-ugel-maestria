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
  attendance_date: string;
  status: string;
  late_minutes: number;
  justification_id: number | null;
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
  const title = navigationItems.find((item) =>
    location.pathname.startsWith(item.to),
  )?.label;

  const logout = async () => {
    try {
      await apiClient.delete("/api/v1/auth/sessions/current");
    } finally {
      onLogout();
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
            <button className="btn btn-sm btn-ghost" type="button" onClick={logout}>
              Salir
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
  const [staffMembers, setStaffMembers] = useState<StaffMember[]>([]);

  useEffect(() => {
    apiClient
      .get<StaffMember[]>("/api/v1/staff-members", { params: { is_active: "Y" } })
      .then((response) => setStaffMembers(response.data))
      .catch(() => setStaffMembers([]));
  }, []);

  return (
    <>
      <PageHeader
        title="Personal"
        description="Registro activo vinculado a la institución educativa"
      />
      <Filters showSearch />
      <section className="card">
        <div className="card-header">Personal activo</div>
        <DataTable
          columns={["DNI", "Apellidos y nombres", "Cargo", "Condición", "Estado"]}
          rows={staffMembers.map((item) => [
            item.dni,
            `${item.last_names}, ${item.first_names}`,
            item.job_title,
            item.employment_status ?? "-",
            item.is_active === "Y" ? "Activo" : "Inactivo",
          ])}
          emptyText="Sin personal registrado"
        />
      </section>
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
      setProcessingLabel("");
    }
  };

  const confirmImport = async () => {
    if (!currentImport) return;
    setLoading(true);
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
      setProcessingLabel("");
    }
  };

  const cancelImport = async () => {
    if (!currentImport) return;
    setLoading(true);
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
              {selectedFile ? "Procesar otra vez" : "Seleccionar archivo"}
            </button>
            <button
              className="btn btn-secondary"
              disabled={!currentImport || loading || currentImport.status !== "draft"}
              onClick={confirmImport}
              type="button"
            >
              Confirmar carga
            </button>
            <button
              className="btn btn-danger-outline"
              disabled={!currentImport || loading}
              onClick={cancelImport}
              type="button"
            >
              Anular carga
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
                          Rebuscar
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
  const [monthImports, setMonthImports] = useState<BiometricImport[]>([]);
  const [attendanceRows, setAttendanceRows] = useState<AttendanceDay[]>([]);
  const [staffMembers, setStaffMembers] = useState<StaffMember[]>([]);
  const [selectedDay, setSelectedDay] = useState<AttendanceDay | null>(null);
  const [selectedStatus, setSelectedStatus] = useState("present");
  const [lateMinutes, setLateMinutes] = useState(0);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const loadAttendance = async () => {
    setLoading(true);
    setError("");
    try {
      const [attendanceResponse, staffResponse] = await Promise.all([
        apiClient.get<AttendanceDay[]>("/api/v1/attendance-records", {
          params: {
            month,
            year,
            import_id: selectedImportId || undefined,
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
    } catch {
      setError("No se pudo cargar la asistencia.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      apiClient.get<AttendanceDay[]>("/api/v1/attendance-records", {
        params: {
          month: initialMonth,
          year: initialYear,
          import_id: selectedImportId || undefined,
        },
      }),
      apiClient.get<StaffMember[]>("/api/v1/staff-members", {
        params: { is_active: "Y" },
      }),
      apiClient.get<BiometricImport[]>("/api/v1/biometric-imports", {
        params: { month: initialMonth, year: initialYear, status: "confirmed" },
      }),
    ])
      .then(([attendanceResponse, staffResponse, importsResponse]) => {
        if (cancelled) return;
        setAttendanceRows(attendanceResponse.data);
        setStaffMembers(staffResponse.data);
        setMonthImports(importsResponse.data);
        if (!selectedImportId && importsResponse.data[0]) {
          setSelectedImportId(importsResponse.data[0].id);
        }
        setSelectedDay(attendanceResponse.data[0] ?? null);
        setSelectedStatus(attendanceResponse.data[0]?.status ?? "present");
        setLateMinutes(attendanceResponse.data[0]?.late_minutes ?? 0);
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
  }, [initialMonth, initialYear, selectedImportId]);

  const loadMonthImports = async (nextMonth: number, nextYear: number) => {
    try {
      const response = await apiClient.get<BiometricImport[]>(
        "/api/v1/biometric-imports",
        { params: { month: nextMonth, year: nextYear, status: "confirmed" } },
      );
      setMonthImports(response.data);
      setSelectedImportId(response.data[0]?.id ?? 0);
    } catch {
      setMonthImports([]);
      setSelectedImportId(0);
    }
  };

  const selectDay = (row: AttendanceDay) => {
    setSelectedDay(row);
    setSelectedStatus(row.status);
    setLateMinutes(row.late_minutes);
    setMessage("");
    setError("");
  };

  const saveDay = async () => {
    if (!selectedDay) return;
    setLoading(true);
    setError("");
    setMessage("");
    try {
      const response = await apiClient.put<AttendanceDay>(
        "/api/v1/attendance-records/days",
        {
          staff_member_id: selectedDay.staff_member_id,
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
      setMessage("Día actualizado");
    } catch {
      setError("No se pudo guardar el día.");
    } finally {
      setLoading(false);
    }
  };

  const staffById = Object.fromEntries(staffMembers.map((staff) => [staff.id, staff]));

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
            <option value="7">Julio</option>
            <option value="6">Junio</option>
            <option value="5">Mayo</option>
          </select>
        </label>
        <label className="form-field">
          <span>Año</span>
          <select
            onChange={(event) => {
              const nextYear = Number(event.target.value);
              setYear(nextYear);
              loadMonthImports(month, nextYear);
            }}
            value={year}
          >
            <option value="2026">2026</option>
          </select>
        </label>
        <label className="form-field grow">
          <span>Archivo</span>
          <select
            onChange={(event) => setSelectedImportId(Number(event.target.value))}
            value={selectedImportId}
          >
            <option value="0">Todos los archivos del mes</option>
            {monthImports.map((item) => (
              <option key={item.id} value={item.id}>
                #{item.id} · {item.file_name}
              </option>
            ))}
          </select>
        </label>
        <div className="filter-actions">
          <button
            className="btn btn-sm btn-primary"
            disabled={loading}
            onClick={loadAttendance}
            type="button"
          >
            Aplicar
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
          <div className="card-header">Día</div>
          <div className="card-body panel-stack">
            <KpiCard
              label="Fecha"
              value={selectedDay?.attendance_date ?? "-"}
              trend={
                selectedDay
                  ? staffById[selectedDay.staff_member_id]?.dni ?? "Personal"
                  : "Seleccione una fila"
              }
            />
            <label className="form-field">
              <span>Estado</span>
              <select
                disabled={!selectedDay}
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
                disabled={!selectedDay}
                min="0"
                onChange={(event) => setLateMinutes(Number(event.target.value))}
                type="number"
                value={lateMinutes}
              />
            </label>
            <button
              className="btn btn-secondary"
              disabled={!selectedDay || loading}
              onClick={saveDay}
              type="button"
            >
              Guardar día
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
  return (
    <>
      <PageHeader
        title="Reportes"
        description="Vista previa de Anexo 03 y Anexo 04 desde asistencia"
      />
      <div className="report-layout">
        <section className="card report-filter">
          <div className="card-header">Filtros</div>
          <div className="card-body">
            <Filters vertical />
            <button className="btn btn-primary btn-block" type="button">
              Generar
            </button>
          </div>
        </section>
        <section className="card report-preview">
          <div className="card-header">Vista previa</div>
          <DataTable
            columns={["Reporte", "Fuente", "Formato"]}
            rows={[
              ["Anexo 03", "attendance_day + institution", "JSON"],
              ["Anexo 04", "attendance_day + institution", "JSON"],
            ]}
          />
        </section>
      </div>
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

function statusText(status: string) {
  const labels: Record<string, string> = {
    draft: "Borrador",
    confirmed: "Confirmada",
    cancelled: "Anulada",
  };
  return labels[status] ?? status;
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
