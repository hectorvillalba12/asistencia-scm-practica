const $ = (id) => document.getElementById(id);
const DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];
const hoy = () => new Date().toLocaleDateString("sv-SE"); // YYYY-MM-DD local

let sesion = JSON.parse(sessionStorage.getItem("sesion") || "null");

/* ---------- utilidades ---------- */

function mostrar(texto, tipo = "ok") {
  const el = $("mensaje");
  el.textContent = texto;
  el.className = `mensaje ${tipo}`;
  clearTimeout(mostrar.timer);
  mostrar.timer = setTimeout(() => (el.className = "mensaje oculto"), 4500);
}

async function api(ruta, opciones = {}) {
  const headers = { "Content-Type": "application/json" };
  if (sesion) headers.Authorization = `Bearer ${sesion.token}`;
  const res = await fetch(`/api${ruta}`, { ...opciones, headers });
  if (res.status === 401 && sesion) {
    cerrarLocal();
    throw new Error("Tu sesión venció, ingresá de nuevo");
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    let msg = data.detail;
    if (Array.isArray(msg)) {
      msg = msg.map((e) => e.msg.replace("Value error, ", "")).join(". ");
    }
    throw new Error(msg || "Ocurrió un error inesperado");
  }
  return data;
}

const post = (ruta, cuerpo) =>
  api(ruta, { method: "POST", body: JSON.stringify(cuerpo) });

function badge(estado) {
  const s = document.createElement("span");
  s.className = `badge ${estado}`;
  s.textContent = estado.replace("_", " ");
  return s;
}

// Usa textContent (no innerHTML) para evitar inyección de HTML
function llenarTabla(tbodyId, filas, columnas) {
  const tbody = $(tbodyId);
  tbody.replaceChildren();
  if (filas.length === 0) {
    const tr = document.createElement("tr");
    const td = document.createElement("td");
    td.colSpan = columnas;
    td.textContent = "Sin registros";
    tr.append(td);
    tbody.append(tr);
    return;
  }
  for (const fila of filas) {
    const tr = document.createElement("tr");
    for (const valor of fila) {
      const td = document.createElement("td");
      if (valor instanceof Node) td.append(valor);
      else td.textContent = valor ?? "—";
      tr.append(td);
    }
    tbody.append(tr);
  }
}

function tarjetas(id, items) {
  const cont = $(id);
  cont.replaceChildren();
  for (const [valor, etiqueta] of items) {
    const div = document.createElement("div");
    const strong = document.createElement("strong");
    strong.textContent = valor;
    const span = document.createElement("span");
    span.textContent = etiqueta;
    div.append(strong, span);
    cont.append(div);
  }
}

function alEnviar(id, accion) {
  $(id).addEventListener("submit", async (ev) => {
    ev.preventDefault();
    try {
      await accion(ev.target);
    } catch (e) {
      mostrar(e.message, "error");
    }
  });
}

const filaResumen = (r) => [
  r.curso, r.total_clases, r.presentes, r.tardanzas, r.ausentes,
  `${r.porcentaje_asistencia}%`, `${r.ausentes}/${r.limite_faltas}`,
  badge(r.regularidad),
];

/* ---------- carga de datos ---------- */

async function cargarCursos() {
  const cursos = await api("/cursos");
  document.querySelectorAll(".sel-curso").forEach((sel) => {
    sel.replaceChildren();
    if (sel.dataset.todos) sel.append(new Option(sel.dataset.todos, ""));
    cursos.forEach((c) => sel.append(new Option(c.nombre, c.id)));
  });
}

async function cargarDocentes() {
  const docentes = await api("/docentes");
  const sel = $("cur-docente");
  sel.replaceChildren();
  docentes.forEach((d) =>
    sel.append(new Option(`${d.apellido}, ${d.nombre}`, d.id))
  );
}

async function cargarHoy() {
  const datos = await api(`/asistencias?fecha=${hoy()}`);
  llenarTabla(
    "hoy-tbody",
    datos.map((a) => [a.hora, a.dni, `${a.apellido}, ${a.nombre}`, a.curso, badge(a.estado)]),
    5
  );
}

/* ---------- formularios ---------- */

alEnviar("form-login", async () => {
  const r = await post("/auth/login", {
    username: $("login-user").value.trim(),
    password: $("login-pass").value,
  });
  sesion = r;
  sessionStorage.setItem("sesion", JSON.stringify(r));
  $("form-login").reset();
  await iniciar();
});

$("btn-logout").addEventListener("click", async () => {
  try {
    await post("/auth/logout", {});
  } finally {
    cerrarLocal();
  }
});

alEnviar("form-asistencia", async () => {
  const r = await post("/asistencias", {
    dni: $("asis-dni").value.trim(),
    curso_id: Number($("asis-curso").value),
    estado: $("asis-estado").value || null,
  });
  mostrar(`${r.apellido}, ${r.nombre}: ${r.estado}${r.hora ? ` (${r.hora})` : ""}`);
  $("asis-dni").value = "";
  $("asis-dni").focus();
  cargarHoy();
});

alEnviar("form-ausentes", async () => {
  const r = await post("/asistencias/ausentes", {
    curso_id: Number($("aus-curso").value),
    fecha: hoy(),
  });
  mostrar(`Se marcaron ${r.marcados} ausente(s)`);
  cargarHoy();
});

alEnviar("form-alumno", async (form) => {
  const body = {
    dni: $("alu-dni").value.trim(),
    nombre: $("alu-nombre").value.trim(),
    apellido: $("alu-apellido").value.trim(),
    password: $("alu-pass").value || null,
  };
  const r = await post("/alumnos", body);
  mostrar(`Alumno guardado: ${r.apellido}, ${r.nombre}`);
  form.reset();
});

alEnviar("form-docente", async (form) => {
  const r = await post("/docentes", {
    dni: $("doc-dni").value.trim(),
    nombre: $("doc-nombre").value.trim(),
    apellido: $("doc-apellido").value.trim(),
    username: $("doc-user").value.trim(),
    password: $("doc-pass").value,
  });
  mostrar(`Docente guardado: ${r.apellido}, ${r.nombre}`);
  form.reset();
  cargarDocentes();
});

alEnviar("form-curso", async (form) => {
  const r = await post("/cursos", {
    nombre: $("cur-nombre").value.trim(),
    docente_id: Number($("cur-docente").value),
    limite_faltas: Number($("cur-limite").value),
  });
  mostrar(`Curso guardado: ${r.nombre}`);
  form.reset();
  cargarCursos();
});

alEnviar("form-horario", async (form) => {
  await post("/horarios", {
    curso_id: Number($("hor-curso").value),
    dia_semana: Number($("hor-dia").value),
    hora_inicio: $("hor-inicio").value,
    hora_fin: $("hor-fin").value,
  });
  mostrar("Horario agregado");
  form.reset();
});

alEnviar("form-inscripcion", async (form) => {
  await post("/inscripciones", {
    dni: $("ins-dni").value.trim(),
    curso_id: Number($("ins-curso").value),
  });
  mostrar("Alumno inscripto");
  form.reset();
});

/* ---------- informes ---------- */

alEnviar("form-total", async () => {
  const cid = $("tot-curso").value;
  const t = await api(`/informes/total${cid ? `?curso_id=${cid}` : ""}`);
  tarjetas("tot-resumen", [
    [t.total_registros, "Registros"],
    [t.presentes, "Presentes"],
    [t.tardanzas, "Tardanzas"],
    [t.ausentes, "Ausentes"],
    [`${t.porcentaje_asistencia}%`, "Asistencia"],
    [t.alumnos_libres, "Alumnos libres"],
  ]);
  llenarTabla(
    "tot-tbody",
    t.filas.map((f) => [`${f.apellido}, ${f.nombre}`, f.dni, ...filaResumen(f)]),
    10
  );
  $("tot-panel").classList.remove("oculto");
});

alEnviar("form-informe", async () => {
  const dni = $("inf-dni").value.trim();
  try {
    const inf = await api(`/informes/alumno/${encodeURIComponent(dni)}`);
    $("inf-titulo").textContent = `${inf.apellido}, ${inf.nombre} (DNI ${inf.dni})`;
    llenarTabla("inf-cursos-tbody", inf.cursos.map(filaResumen), 8);
    llenarTabla(
      "inf-tbody",
      inf.detalle.map((a) => [a.fecha, a.hora, a.curso, badge(a.estado)]),
      4
    );
    $("inf-panel").classList.remove("oculto");
  } catch (e) {
    $("inf-panel").classList.add("oculto");
    throw e;
  }
});

/* ---------- inicio ---------- */

function cerrarLocal() {
  sesion = null;
  sessionStorage.removeItem("sesion");
  iniciar();
}

async function iniciar() {
  $("login").classList.toggle("oculto", !!sesion);
  $("app").classList.toggle("oculto", !sesion);
  $("sesion-info").classList.toggle("oculto", !sesion);
  if (!sesion) return;

  $("usuario-nombre").textContent = `${sesion.username} (${sesion.rol})`;
  document.querySelectorAll("[data-roles]").forEach((el) => {
    el.classList.toggle("oculto", !el.dataset.roles.split(" ").includes(sesion.rol));
  });

  try {
    if (sesion.rol === "alumno") {
      $("inf-dni").value = sesion.username;
      $("inf-dni").readOnly = true;
      $("form-informe").requestSubmit();
      return;
    }
    await cargarCursos();
    if (sesion.rol === "admin") await cargarDocentes();
    await cargarHoy();
  } catch (e) {
    mostrar(e.message, "error");
  }
}

$("fecha-hoy").textContent = new Date().toLocaleDateString("es-AR", {
  weekday: "long", day: "numeric", month: "long", year: "numeric",
});
DIAS.forEach((d, i) => $("hor-dia").append(new Option(d, i)));
iniciar();