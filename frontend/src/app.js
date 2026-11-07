const API_URL = window.BIBLIONEXO_API_URL || "http://127.0.0.1:8000/api/v1";
const currentUser = JSON.parse(localStorage.getItem("biblionexo_user") || "null");

if (!currentUser || !currentUser.access_token) {
    window.location.href = "index.html";
} else {
    document.getElementById("user-badge").innerText = `${currentUser.nombre} (${currentUser.rol})`;
}

function authHeaders() {
    return {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${currentUser.access_token}`
    };
}

function showFeedback(okMsg, errMsg) {
    const okEl = document.getElementById("global-ok");
    const errEl = document.getElementById("global-err");
    okEl.style.display = okMsg ? "block" : "none";
    okEl.innerText = okMsg || "";
    errEl.style.display = errMsg ? "block" : "none";
    errEl.innerText = errMsg || "";
}

function logout() {
    localStorage.removeItem("biblionexo_user");
    window.location.href = "index.html";
}

function switchTab(evt, secId) {
    showFeedback(null, null);
    document.querySelectorAll(".tab-section").forEach(el => el.classList.remove("active"));
    document.querySelectorAll(".nav-tabs button").forEach(el => el.classList.remove("active"));
    document.getElementById(secId).classList.add("active");
    evt.currentTarget.classList.add("active");

    if (secId === "sec-prestamos") cargarPrestamos();
    if (secId === "sec-libros") cargarLibros();
    if (secId === "sec-usuarios") cargarUsuarios();
    if (secId === "sec-vencimientos") cargarVencimientos();
    if (secId === "sec-sanciones") cargarSanciones();
}

// 1. Disponibilidad
async function buscarDisponibilidad(event) {
    event.preventDefault();
    showFeedback(null, null);
    const criterio = document.getElementById("disp-criterio").value.trim();
    const cont = document.getElementById("disp-resultados");
    cont.innerHTML = "";
    try {
        const res = await fetch(`${API_URL}/disponibilidad?criterio=${encodeURIComponent(criterio)}`, {
            headers: authHeaders()
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Error al consultar disponibilidad");

        if (data.mensaje) {
            cont.innerHTML = `<div class="card"><p><strong>${data.mensaje}</strong></p></div>`;
            return;
        }
        cont.innerHTML = data.libros.map(item => {
            let estadoHtml = "";
            if (item.sin_ejemplares) {
                estadoHtml = `<p><strong>Sin ejemplares registrados</strong></p>`;
            } else {
                const banner = item.disponibles === 0
                    ? `<p class="alert-err">No hay ejemplares disponibles para este título.</p>`
                    : `<p class="alert-ok">Ejemplares disponibles: ${item.disponibles} de ${item.total_ejemplares}</p>`;
                const filas = item.ejemplares.map(ej => `
                    <tr>
                        <td>${ej.id}</td>
                        <td>${ej.codigo_inventario}</td>
                        <td>${ej.ubicacion}</td>
                        <td><span class="${ej.disponible ? 'badge-disp' : 'badge-prest'}">${ej.estado}</span></td>
                    </tr>
                `).join("");
                estadoHtml = `${banner}
                    <table>
                        <thead><tr><th>ID Ejemplar</th><th>Código Inventario</th><th>Ubicación</th><th>Estado</th></tr></thead>
                        <tbody>${filas}</tbody>
                    </table>`;
            }
            return `<div class="card">
                <h3>${item.titulo} <small>(${item.isbn})</small></h3>
                <p>Autor: ${item.autor} · Categoría: ${item.categoria}</p>
                ${estadoHtml}
            </div>`;
        }).join("");
    } catch (err) {
        showFeedback(null, err.message);
    }
}

// 2. Préstamos y Devoluciones
async function cargarPrestamos() {
    const soloActivos = document.getElementById("prest-solo-activos").checked;
    const res = await fetch(`${API_URL}/prestamos?solo_activos=${soloActivos}`, { headers: authHeaders() });
    const data = await res.json();
    if (!res.ok) return showFeedback(null, data.detail || "Error al cargar préstamos");
    const tbody = document.getElementById("tabla-prestamos");
    tbody.innerHTML = data.map(p => `
        <tr>
            <td>#${p.id}</td>
            <td>#${p.usuario_id} (${p.usuario_nombre})</td>
            <td>#${p.ejemplar_id} (${p.codigo_inventario} — ${p.libro_titulo})</td>
            <td>${p.fecha_prestamo}</td>
            <td>${p.fecha_limite}</td>
            <td>${p.fecha_devolucion || "Activo"}</td>
        </tr>
    `).join("");
}

async function crearPrestamo(event) {
    event.preventDefault();
    showFeedback(null, null);
    const payload = {
        usuario_id: parseInt(document.getElementById("prest-usuario").value, 10),
        ejemplar_id: parseInt(document.getElementById("prest-ejemplar").value, 10),
        fecha_limite: document.getElementById("prest-limite").value
    };
    const res = await fetch(`${API_URL}/prestamos`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok) return showFeedback(null, data.detail || "Error al registrar préstamo");
    showFeedback(data.mensaje, null);
    cargarPrestamos();
}

async function devolverPrestamo(event) {
    event.preventDefault();
    showFeedback(null, null);
    const payload = {
        prestamo_id: parseInt(document.getElementById("dev-prestamo").value, 10)
    };
    const res = await fetch(`${API_URL}/prestamos/devolver`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok) return showFeedback(null, data.detail || "Error al registrar devolución");
    showFeedback(data.mensaje, null);
    cargarPrestamos();
}

// 3. Libros
async function cargarLibros(q = "") {
    const res = await fetch(`${API_URL}/libros?q=${encodeURIComponent(q)}`, { headers: authHeaders() });
    const data = await res.json();
    if (!res.ok) return showFeedback(null, data.detail || "Error al cargar libros");
    const tbody = document.getElementById("tabla-libros");
    tbody.innerHTML = data.map(l => `
        <tr>
            <td>${l.id}</td>
            <td>${l.isbn}</td>
            <td>${l.titulo}</td>
            <td>${l.autor}</td>
            <td>${l.categoria}</td>
            <td>${(l.ejemplares || []).length}</td>
        </tr>
    `).join("");
}

function filtrarLibros(event) {
    event.preventDefault();
    cargarLibros(document.getElementById("lib-q").value);
}

async function crearLibro(event) {
    event.preventDefault();
    showFeedback(null, null);
    const payload = {
        isbn: document.getElementById("lib-isbn").value,
        titulo: document.getElementById("lib-titulo").value,
        autor: document.getElementById("lib-autor").value,
        categoria: document.getElementById("lib-categoria").value,
        cantidad_ejemplares: parseInt(document.getElementById("lib-cantidad").value, 10),
        ubicacion: document.getElementById("lib-ubicacion").value
    };
    const res = await fetch(`${API_URL}/libros`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok) return showFeedback(null, data.detail || "Error al guardar libro");
    showFeedback(`Libro '${data.titulo}' registrado con ${(data.ejemplares || []).length} ejemplares.`, null);
    cargarLibros();
}

// 4. Usuarios
async function cargarUsuarios(q = "") {
    const res = await fetch(`${API_URL}/usuarios?q=${encodeURIComponent(q)}`, { headers: authHeaders() });
    const data = await res.json();
    if (!res.ok) return showFeedback(null, data.detail || "Error al cargar usuarios");
    const tbody = document.getElementById("tabla-usuarios");
    tbody.innerHTML = data.map(u => `
        <tr>
            <td>${u.id}</td>
            <td>${u.nombre}</td>
            <td>${u.correo}</td>
            <td>${u.rol}</td>
        </tr>
    `).join("");
}

function filtrarUsuarios(event) {
    event.preventDefault();
    cargarUsuarios(document.getElementById("usu-q").value);
}

async function crearUsuario(event) {
    event.preventDefault();
    showFeedback(null, null);
    const payload = {
        nombre: document.getElementById("usu-nombre").value,
        correo: document.getElementById("usu-correo").value,
        rol: document.getElementById("usu-rol").value,
        password: document.getElementById("usu-password").value
    };
    const res = await fetch(`${API_URL}/usuarios`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok) return showFeedback(null, data.detail || "Error al registrar usuario");
    showFeedback(`Usuario '${data.nombre}' registrado con ID #${data.id}.`, null);
    cargarUsuarios();
}

// 5. Vencimientos
async function cargarVencimientos() {
    const res = await fetch(`${API_URL}/vencimientos`, { headers: authHeaders() });
    const data = await res.json();
    if (!res.ok) return showFeedback(null, data.detail || "Error al cargar vencimientos");
    document.getElementById("venc-fecha-corte").innerText = `(Fecha de corte: ${data.fecha_corte})`;
    const tbody = document.getElementById("tabla-vencimientos");
    if (!data.vencidos.length) {
        tbody.innerHTML = `<tr><td colspan="6">No existen préstamos vencidos pendientes de devolución.</td></tr>`;
        return;
    }
    tbody.innerHTML = data.vencidos.map(v => `
        <tr>
            <td>#${v.prestamo_id}</td>
            <td>#${v.usuario_id} — ${v.usuario_nombre}</td>
            <td>${v.libro_titulo} (${v.codigo_inventario})</td>
            <td>${v.fecha_prestamo}</td>
            <td>${v.fecha_limite}</td>
            <td><strong>${v.dias_atraso} días</strong></td>
        </tr>
    `).join("");
}

// 6. Sanciones
async function cargarSanciones() {
    const res = await fetch(`${API_URL}/sanciones`, { headers: authHeaders() });
    const data = await res.json();
    if (!res.ok) return showFeedback(null, data.detail || "Error al cargar sanciones");
    const tbody = document.getElementById("tabla-sanciones");
    tbody.innerHTML = data.map(s => `
        <tr>
            <td>#${s.id}</td>
            <td>#${s.usuario_id} (${s.usuario_nombre})</td>
            <td>${s.prestamo_id || "—"}</td>
            <td>${s.motivo}</td>
            <td>${s.fecha_inicio}</td>
            <td>${s.fecha_fin}</td>
            <td>${s.estado}</td>
        </tr>
    `).join("");
}

async function crearSancion(event) {
    event.preventDefault();
    showFeedback(null, null);
    const pidRaw = document.getElementById("sanc-prestamo").value.trim();
    const payload = {
        usuario_id: parseInt(document.getElementById("sanc-usuario").value, 10),
        prestamo_id: pidRaw ? parseInt(pidRaw, 10) : null,
        motivo: document.getElementById("sanc-motivo").value,
        fecha_fin: document.getElementById("sanc-fin").value
    };
    const res = await fetch(`${API_URL}/sanciones`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok) return showFeedback(null, data.detail || "Error al registrar sanción");
    showFeedback(data.mensaje, null);
    cargarSanciones();
}
