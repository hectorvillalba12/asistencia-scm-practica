const $ = (id) => document.getElementById(id);
const hoy = () => new Date().toLocaleDateString("sv-SE"); // YYYY-MM-DD en hora local

/* ---------- utilidades ---------- */

function mostrar(texto, tipo = "ok") {
  const el = $("mensaje");
  el.textContent = texto;
  el.className = `mensaje ${tipo}`;
  clearTimeout(mostrar.timer);
  mostrar.timer = setTimeout(() => (el.className = "mensaje oculto"), 4500);
}

async function api(ruta, opciones = {}) {
  const res = await fetch(`/api${ruta}`, {
    headers: { "Content-Type": "application/json" },
    ...opciones,
  });
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

function badge(estado) {
  const s = document.createElement("span");
  s.className = `badge ${estado}`;
  s.textContent = estado;
  return s;
}

// Usa textContent (no innerHTML) para evitar inyección de HTML
function llenarTabla(tbodyId, filas) {
  const tbody = $(tbodyId);
  tbody.replaceChildren();
  if (filas.length === 0) {
    const tr = document.createElement("tr");
    const td = document.createElement("td");
    td.colSpan = 5;
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

/* ---------- registros de hoy ---------- */

async function cargarHoy() {
  try {
    const datos = await api(`/asistencias?fecha=${hoy()}`);
    llenarTabla(
      "hoy-tbody",
      datos.map((a) => [a.hora, a.dni, `${a.apellido}, ${a.nombre}`, a.materia, badge(a.estado)])
    );
  } catch (e) {
    mostrar(e.message, "error");
  }
}

/* ---------- formularios ---------- */

$("form-asistencia").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const body = {
    dni: $("asis-dni").value.trim(),
    materia: $("asis-materia").value.trim(),
    estado: $("asis-estado").value || null,
  };
  try {
    const r = await api("/asistencias", { method: "POST", body: JSON.stringify(body) });
    mostrar(`${r.apellido}, ${r.nombre}: ${r.estado}${r.hora ? ` (${r.hora})` : ""}`);
    $("asis-dni").value = "";
    $("asis-dni").focus();
    cargarHoy();
  } catch (e) {
    mostrar(e.message, "error");
  }
});

$("form-alumno").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const body = {
    dni: $("alu-dni").value.trim(),
    nombre: $("alu-nombre").value.trim(),
    apellido: $("alu-apellido").value.trim(),
  };
  try {
    const r = await api("/alumnos", { method: "POST", body: JSON.stringify(body) });
    mostrar(`Alumno guardado: ${r.apellido}, ${r.nombre}`);
    ev.target.reset();
  } catch (e) {
    mostrar(e.message, "error");
  }
});

$("form-ausentes").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const body = { materia: $("aus-materia").value.trim(), fecha: hoy() };
  try {
    const r = await api("/asistencias/ausentes", { method: "POST", body: JSON.stringify(body) });
    mostrar(`Se marcaron ${r.marcados} ausente(s)`);
    cargarHoy();
  } catch (e) {
    mostrar(e.message, "error");
  }
});

$("form-informe").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const dni = $("inf-dni").value.trim();
  const materia = $("inf-materia").value.trim();
  const query = materia ? `?materia=${encodeURIComponent(materia)}` : "";
  try {
    const inf = await api(`/alumnos/${encodeURIComponent(dni)}/informe${query}`);

    $("inf-titulo").textContent =
      `${inf.apellido}, ${inf.nombre} (DNI ${inf.dni})` + (inf.materia ? ` - ${inf.materia}` : "");

    const resumen = $("inf-resumen");
    resumen.replaceChildren();
    const items = [
      [inf.total_clases, "Clases"],
      [inf.presentes, "Presentes"],
      [inf.tardanzas, "Tardanzas"],
      [inf.ausentes, "Ausentes"],
      [`${inf.porcentaje_asistencia}%`, "Asistencia"],
    ];
    for (const [valor, etiqueta] of items) {
      const div = document.createElement("div");
      const strong = document.createElement("strong");
      strong.textContent = valor;
      const span = document.createElement("span");
      span.textContent = etiqueta;
      div.append(strong, span);
      resumen.append(div);
    }

    llenarTabla(
      "inf-tbody",
      inf.detalle.map((a) => [a.fecha, a.hora, a.materia, badge(a.estado)])
    );
    $("informe").classList.remove("oculto");
  } catch (e) {
    $("informe").classList.add("oculto");
    mostrar(e.message, "error");
  }
});

/* ---------- inicio ---------- */

$("fecha-hoy").textContent = new Date().toLocaleDateString("es-AR", {
  weekday: "long", day: "numeric", month: "long", year: "numeric",
});
cargarHoy();