/**
 * EnchufaTE · Frontend Interactive Logic
 * Motor Inteligente de Dimensionamiento y Electrificación Rural Off-Grid
 * Flujo tipo asistente de 5 pasos que se desbloquean progresivamente:
 * 1. Ubicación -> 2. Detalles -> 3. Cálculo (3 opciones) -> 4. Plano -> 5. Expediente TE1
 */

const STEP_TABS = ['tab-mapa', 'tab-detalles', 'tab-calculo', 'tab-plano', 'tab-te1'];

// Estado Global de la Aplicación
const state = {
  location: {
    latitude: -35.96,
    longitude: -72.31,
    region_id: 'maule',
    locality_name: 'Sector Rural Cauquenes'
  },
  inhabitants: 4,
  households: 1,
  preferredOption: null, // null = recomendada (automática) | 'economica' | 'recomendada' | 'resiliente'
  appliances: [],
  presets: {},
  lastResult: null,
  isStandMode800x480: false,
  currentStepIndex: 0,
  maxUnlockedStep: 0,
  mapPickerInstance: null,
  mapPickerMarker: null,
  mapLayoutInstance: null,
  mapLayoutLayerGroup: null
};

// ================= MANEJO DE ERRORES VISIBLE (nunca falla en silencio) =================
function setupErrorBanner() {
  const closeBtn = document.getElementById('error-banner-close');
  if (closeBtn) closeBtn.addEventListener('click', hideError);

  // Cualquier excepción no capturada en el código, o promesa rechazada sin .catch,
  // se muestra igual en el banner en vez de perderse silenciosamente en la consola.
  window.addEventListener('error', (e) => {
    showError(`Error inesperado: ${e.message || e}`);
  });
  window.addEventListener('unhandledrejection', (e) => {
    const reason = e.reason && e.reason.message ? e.reason.message : e.reason;
    showError(`Error inesperado: ${reason}`);
  });
}

function showError(message, retryFn) {
  console.error(message);
  const banner = document.getElementById('error-banner');
  const text = document.getElementById('error-banner-text');
  if (!banner || !text) {
    alert(message);
    return;
  }
  text.textContent = message;

  // Botón "Reintentar" opcional (ej: cuando el problema es de conexión con el backend)
  let retryBtn = document.getElementById('error-banner-retry');
  if (retryBtn) retryBtn.remove();
  if (retryFn) {
    retryBtn = document.createElement('button');
    retryBtn.id = 'error-banner-retry';
    retryBtn.className = 'error-banner-retry';
    retryBtn.textContent = 'Reintentar';
    retryBtn.addEventListener('click', () => {
      hideError();
      retryFn();
    });
    banner.insertBefore(retryBtn, document.getElementById('error-banner-close'));
  }

  banner.classList.remove('hidden');
}

function hideError() {
  const banner = document.getElementById('error-banner');
  if (banner) banner.classList.add('hidden');
}

function runSafely(label, fn) {
  try {
    fn();
  } catch (err) {
    showError(`${label}: ${err.message || err}`);
  }
}

// Un fetch() rechazado (no una respuesta HTTP con error) significa que el navegador ni
// siquiera pudo conectarse al servidor: backend caído, puerto equivocado, CORS bloqueado,
// o la página abierta como archivo local (file://) en vez de servida por el backend.
function isNetworkLevelError(err) {
  return err instanceof TypeError;
}

function friendlyConnectionMessage(err) {
  if (isNetworkLevelError(err)) {
    if (window.location.protocol === 'file:') {
      return 'No se pudo conectar con el servidor: esta página se abrió como archivo local (file://). ' +
        'Debes iniciar el backend con "python backend/run.py" y abrir http://localhost:8000 en el navegador, no el archivo index.html directamente.';
    }
    return `No se pudo conectar con el servidor backend en ${window.location.origin}. ` +
      'Verifica que esté corriendo (python backend/run.py) y que no haya un firewall/proxy bloqueando la conexión.';
  }
  return err.message || String(err);
}

// Inicialización
document.addEventListener('DOMContentLoaded', async () => {
  setupErrorBanner();

  if (window.location.protocol === 'file:') {
    showError(
      'Esta página se abrió como archivo local (file://) y no puede conectarse al servidor. ' +
      'Inicia el backend con "python backend/run.py" desde la carpeta del proyecto y abre http://localhost:8000 en el navegador.'
    );
  }

  runSafely('Error iniciando la navegación por pasos', setupStepper);
  runSafely('Error iniciando el modo stand', setupStandModeToggle);
  runSafely('Error iniciando el formulario de equipos', setupModal);
  runSafely('Error iniciando los controles', setupEventListeners);
  runSafely('Error iniciando el mapa de ubicación', setupMapPicker);

  await loadInitialData();
  await runDimensioning();
});

// ================= NAVEGACIÓN DEL ASISTENTE (WIZARD) =================
function setupStepper() {
  document.querySelectorAll('.step-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      if (btn.disabled) return;
      goToStep(btn.dataset.tab);
    });
  });

  document.querySelectorAll('.btn-continue').forEach(btn => {
    btn.addEventListener('click', () => {
      if (btn.disabled) return;
      const stepIdx = parseInt(btn.dataset.step, 10);
      unlockStep(stepIdx + 1);
      goToStep(btn.dataset.next);
    });
  });

  document.querySelectorAll('.btn-back').forEach(btn => {
    btn.addEventListener('click', () => goToStep(btn.dataset.prev));
  });

  updateStepperUI();
}

function goToStep(tabId) {
  const idx = STEP_TABS.indexOf(tabId);
  if (idx === -1) return;

  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
  document.getElementById(tabId).classList.add('active');
  state.currentStepIndex = idx;
  updateStepperUI();

  // Leaflet requiere invalidateSize() al mostrar un mapa que estaba en un tab oculto
  if (tabId === 'tab-mapa' && state.mapPickerInstance) {
    setTimeout(() => state.mapPickerInstance.invalidateSize(), 50);
  }
  if (tabId === 'tab-plano' && state.mapLayoutInstance) {
    setTimeout(() => state.mapLayoutInstance.invalidateSize(), 50);
  }

  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function unlockStep(idx) {
  state.maxUnlockedStep = Math.max(state.maxUnlockedStep, idx);
  updateStepperUI();
}

function updateStepperUI() {
  document.querySelectorAll('.step-btn').forEach(btn => {
    const idx = parseInt(btn.dataset.step, 10);
    const locked = idx > state.maxUnlockedStep;
    btn.classList.toggle('active', idx === state.currentStepIndex);
    btn.classList.toggle('done', idx < state.currentStepIndex && idx <= state.maxUnlockedStep);
    btn.classList.toggle('locked', locked);
    btn.disabled = locked;
    const numEl = btn.querySelector('.step-num');
    numEl.textContent = (idx < state.currentStepIndex && idx <= state.maxUnlockedStep) ? '✓' : String(idx + 1);
  });
  document.querySelectorAll('.step-connector').forEach((conn, i) => {
    conn.classList.toggle('done', i < state.maxUnlockedStep);
  });
}

// ================= MODO STAND 800x480 =================
function setupStandModeToggle() {
  const btn = document.getElementById('btn-toggle-800x480');
  const wrapper = document.getElementById('app-wrapper');

  btn.addEventListener('click', () => {
    state.isStandMode800x480 = !state.isStandMode800x480;
    if (state.isStandMode800x480) {
      wrapper.classList.add('mode-800x480');
      btn.classList.add('active');
    } else {
      wrapper.classList.remove('mode-800x480');
      btn.classList.remove('active');
    }
    if (state.mapPickerInstance) setTimeout(() => state.mapPickerInstance.invalidateSize(), 100);
    if (state.mapLayoutInstance) setTimeout(() => state.mapLayoutInstance.invalidateSize(), 100);
  });
}

// ================= CARGA DE DATOS INICIALES =================
async function loadInitialData() {
  try {
    // Presets de Casos de Uso (solo afectan habitantes/artefactos, no la ubicación ya elegida)
    const resPre = await fetch('/api/presets');
    if (resPre.ok) {
      state.presets = await resPre.json();
    } else {
      showError(`No se pudieron cargar los presets del servidor (HTTP ${resPre.status}).`);
    }

    // Catálogo Base de Artefactos
    const resCat = await fetch('/api/catalogo');
    if (!resCat.ok) {
      showError(`No se pudo cargar el catálogo de electrodomésticos (HTTP ${resCat.status}). No podrás avanzar al paso 2 correctamente.`, () => loadInitialData());
      return;
    }
    const catalog = await resCat.json();
    state.appliances = catalog.map(item => ({
      ...item,
      enabled: item.id === 'refrigerador_inverter' || item.id === 'starlink_internet' ||
               item.id === 'bomba_agua_05hp' || item.id === 'iluminacion_led_rural' ||
               item.id === 'cargadores_dispositivos' || item.id === 'televisor_smart_led'
    }));
    renderAppliancesList();
  } catch (err) {
    showError(`No se pudieron cargar los datos iniciales. ${friendlyConnectionMessage(err)}`, () => loadInitialData());
  }
}

// ================= EVENT LISTENERS =================
function setupEventListeners() {
  // Cambio de Preset (solo afecta habitantes y artefactos)
  document.getElementById('select-preset').addEventListener('change', (e) => {
    applyPreset(e.target.value);
  });

  // Slider de Habitantes
  const rangeInh = document.getElementById('input-inhabitants');
  rangeInh.addEventListener('input', (e) => {
    const count = parseInt(e.target.value, 10);
    state.inhabitants = count;
    document.getElementById('val-inhabitants-count').textContent = `${count} ${count === 1 ? 'persona' : 'personas'}`;
    runDimensioning();
  });

  // Slider de Viviendas / Instalaciones a electrificar
  const rangeHouseholds = document.getElementById('input-households');
  rangeHouseholds.addEventListener('input', (e) => {
    const count = parseInt(e.target.value, 10);
    state.households = count;
    document.getElementById('val-households-count').textContent = `${count} ${count === 1 ? 'vivienda' : 'viviendas'}`;
    runDimensioning();
  });

  // Búsqueda de dirección/localidad en el mapa
  document.getElementById('btn-map-search').addEventListener('click', () => {
    searchLocality();
  });
  document.getElementById('map-search-input').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      searchLocality();
    }
  });
}

// ================= APLICAR PRESETS (solo habitantes + artefactos) =================
function applyPreset(presetKey) {
  const preset = state.presets[presetKey];
  if (!preset) return;

  state.inhabitants = preset.inhabitants || 4;
  document.getElementById('input-inhabitants').value = state.inhabitants;
  document.getElementById('val-inhabitants-count').textContent = `${state.inhabitants} personas`;

  // Actualizar artefactos del preset
  if (preset.appliances && preset.appliances.length > 0) {
    const presetAppMap = new Map(preset.appliances.map(a => [a.id, a]));
    state.appliances.forEach(app => {
      if (presetAppMap.has(app.id)) {
        const pApp = presetAppMap.get(app.id);
        app.enabled = true;
        if (pApp.quantity) app.quantity = pApp.quantity;
        if (pApp.hours_per_day) app.hours_per_day = pApp.hours_per_day;
      } else {
        app.enabled = false;
      }
    });
    renderAppliancesList();
  }

  runDimensioning();
}

// ================= RENDERIZADO DE ARTEFACTOS =================
function renderAppliancesList() {
  const container = document.getElementById('appliances-container');
  container.innerHTML = '';

  state.appliances.forEach((app, idx) => {
    const card = document.createElement('div');
    card.className = `appliance-item-card ${app.enabled ? '' : 'disabled'}`;

    const dailyWh = Math.round(app.power_w * app.hours_per_day * app.quantity * (app.duty_cycle || 1.0));

    card.innerHTML = `
      <div class="appliance-left">
        <input type="checkbox" id="chk-app-${idx}" ${app.enabled ? 'checked' : ''} class="app-chk">
        <div>
          <div class="appliance-title">${escapeHtml(app.name)}</div>
          <div class="appliance-meta">${app.power_w}W · ${app.hours_per_day}h/día</div>
        </div>
      </div>
      <div class="appliance-right">
        <button class="app-qty-btn btn-qty-minus" data-idx="${idx}">-</button>
        <span style="font-size:11px;font-weight:700;min-width:14px;text-align:center;">${app.quantity}</span>
        <button class="app-qty-btn btn-qty-plus" data-idx="${idx}">+</button>
        <div class="appliance-energy">${dailyWh} Wh</div>
      </div>
    `;

    const chk = card.querySelector('.app-chk');
    chk.addEventListener('change', (e) => {
      app.enabled = e.target.checked;
      renderAppliancesList();
      runDimensioning();
    });

    card.querySelector('.btn-qty-minus').addEventListener('click', () => {
      if (app.quantity > 1) {
        app.quantity -= 1;
        renderAppliancesList();
        runDimensioning();
      }
    });

    card.querySelector('.btn-qty-plus').addEventListener('click', () => {
      app.quantity += 1;
      renderAppliancesList();
      runDimensioning();
    });

    container.appendChild(card);
  });
}

// ================= LLAMADA AL MOTOR DE DIMENSIONAMIENTO =================
async function runDimensioning() {
  const payload = {
    location: state.location,
    inhabitants: state.inhabitants,
    households: state.households,
    appliances: state.appliances,
    preferred_option: state.preferredOption
  };

  try {
    const response = await fetch('/api/dimensionar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      let detail = `HTTP ${response.status}`;
      try {
        const errBody = await response.json();
        if (errBody && errBody.detail) {
          detail = typeof errBody.detail === 'string' ? errBody.detail : JSON.stringify(errBody.detail);
        }
      } catch (_parseErr) {
        // El cuerpo del error no era JSON; se usa el código HTTP tal cual.
      }
      throw new Error(detail);
    }

    const data = await response.json();
    state.lastResult = data;
    hideError();
    updateUI(data);
  } catch (err) {
    const message = friendlyConnectionMessage(err);
    showError(`No se pudo calcular el dimensionamiento. ${message}`, () => runDimensioning());
    renderInlineErrorState('options-comparison-container', message, () => runDimensioning());
  }
}

// Muestra un estado de error visible dentro de un contenedor de contenido específico
// (en vez de dejarlo vacío en silencio), con botón para reintentar.
function renderInlineErrorState(containerId, message, onRetry) {
  const container = document.getElementById(containerId);
  if (!container) return;
  container.innerHTML = `
    <div class="inline-error-state">
      <div class="ie-icon">⚠️</div>
      <div class="ie-text">No se pudo cargar esta sección: ${escapeHtml(message)}</div>
      <button class="btn-primary" id="btn-retry-${containerId}">Reintentar</button>
    </div>
  `;
  const retryBtn = document.getElementById(`btn-retry-${containerId}`);
  if (retryBtn) retryBtn.addEventListener('click', onRetry);
}

// ================= ACTUALIZAR TODA LA INTERFAZ =================
// Cada paso se actualiza en su propio try/catch: si uno falla, el resto de la interfaz
// sigue funcionando y el error queda visible en el banner (nunca se cae en silencio).
function updateUI(data) {
  runSafely('Error mostrando ubicación/clima (Paso 1)', () => updateLocationAndClimateUI(data));
  runSafely('Error mostrando demanda (Paso 2)', () => updateDemandUI(data));
  runSafely('Error mostrando la comparativa de opciones (Paso 3)', () => renderOptionsComparison(data));
  runSafely('Error mostrando el plano de instalación (Paso 4)', () => renderInstallationLayout(data));
  runSafely('Error mostrando el expediente TE1 SEC (Paso 5)', () => {
    updateTe1Tab(data);
    renderSecChecklist(data.sec_compliance.checklist);
  });
}

function updateLocationAndClimateUI(data) {
  const climate = data.climate;
  document.getElementById('val-climate-psh').innerHTML = `${climate.psh.toFixed(1)} <span class="unit">kWh/m²/día</span>`;
  document.getElementById('val-climate-wind').innerHTML = `${climate.wind_speed_avg_ms.toFixed(1)} <span class="unit">m/s</span>`;
  document.getElementById('weather-source-badge').textContent = climate.source.includes('open_meteo') ? 'Open-Meteo Live' : 'Modelo Regional';

  const badgeWind = document.getElementById('badge-wind-feasibility');
  if (climate.wind_feasible) {
    badgeWind.textContent = 'Eólica Viable (≥ 4.5 m/s) · Posible Sistema Híbrido';
    badgeWind.className = 'wind-status-badge feasible';
  } else {
    badgeWind.textContent = 'Eólica no viable (< 4.5 m/s) · Sistema 100% Solar';
    badgeWind.className = 'wind-status-badge';
  }

  document.getElementById('map-lat-lon').textContent = `${data.location.latitude.toFixed(4)}° Lat, ${data.location.longitude.toFixed(4)}° Lon`;
}

function updateDemandUI(data) {
  const demand = data.demand;
  document.getElementById('badge-total-kwh').textContent = `${demand.total_daily_kwh.toFixed(2)} kWh/día`;
  document.getElementById('val-peak-power').textContent = `${(demand.peak_synchronous_power_w / 1000).toFixed(2)} kW`;
  document.getElementById('val-surge-power').textContent = `${(demand.peak_surge_power_w / 1000).toFixed(2)} kW`;
}

// ================= MAPAS (LEAFLET) =================
// CARTO Positron (gratuito, sin API key). Se usa en vez de tile.openstreetmap.org porque
// muchos entornos de hosting/cloud reciben "403 Access Blocked" del tile server estándar de
// OpenStreetMap (bloquea rangos de IP de datacenters por política anti-abuso). Las tiles de
// CARTO están pensadas justamente para este tipo de embebido sin registro y además calzan
// con el tema claro de la interfaz.
const TILE_LAYER_URL = 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png';
const TILE_LAYER_OPTIONS = {
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
  subdomains: 'abcd',
  maxZoom: 19
};

/** Agrega la capa de tiles a un mapa Leaflet y avisa visiblemente (una sola vez) si las tiles no cargan. */
function addTileLayerWithErrorHandling(map, mapLabel) {
  const layer = L.tileLayer(TILE_LAYER_URL, TILE_LAYER_OPTIONS).addTo(map);
  let warned = false;
  layer.on('tileerror', () => {
    if (warned) return;
    warned = true;
    showError(
      `No se pudieron cargar las imágenes del ${mapLabel} (posible bloqueo de red). ` +
      'Igual puedes hacer clic en el área del mapa para fijar coordenadas, o escribir la dirección.'
    );
  });
  return layer;
}

// ================= PASO 1: MAPA / UBICACIÓN (LEAFLET) =================
function setupMapPicker() {
  const el = document.getElementById('map-picker');
  if (!el || typeof L === 'undefined') {
    showError('No se pudo inicializar el mapa: la librería Leaflet no cargó (revisa tu conexión a internet).');
    return;
  }

  const map = L.map('map-picker', { zoomControl: true }).setView([state.location.latitude, state.location.longitude], 11);
  addTileLayerWithErrorHandling(map, 'mapa de ubicación');

  const marker = L.marker([state.location.latitude, state.location.longitude], { draggable: true }).addTo(map);

  const setLocationFromLatLng = (lat, lon) => {
    state.location.latitude = Math.round(lat * 10000) / 10000;
    state.location.longitude = Math.round(lon * 10000) / 10000;
    document.getElementById('map-lat-lon').textContent = `${state.location.latitude.toFixed(4)}° Lat, ${state.location.longitude.toFixed(4)}° Lon`;
    reverseGeocodeLocality(state.location.latitude, state.location.longitude);
    runDimensioning();
  };

  map.on('click', (e) => {
    marker.setLatLng(e.latlng);
    setLocationFromLatLng(e.latlng.lat, e.latlng.lng);
  });

  marker.on('dragend', () => {
    const pos = marker.getLatLng();
    setLocationFromLatLng(pos.lat, pos.lng);
  });

  state.mapPickerInstance = map;
  state.mapPickerMarker = marker;
}

// Geocodificación inversa vía el backend (proxy a Nominatim con User-Agent identificable;
// evita el error "referer is required" que ocurre al llamar a OpenStreetMap directo desde el navegador)
async function reverseGeocodeLocality(lat, lon) {
  try {
    const resp = await fetch(`/api/geocode/reverse?lat=${lat}&lon=${lon}`);
    if (!resp.ok) return;
    const data = await resp.json();
    if (data.display_name) {
      state.location.locality_name = data.display_name;
      document.getElementById('map-locality-name').textContent = data.display_name;
    }
    if (data.comuna || data.region_name) {
      document.getElementById('map-region-comuna').textContent = [data.region_name, data.comuna].filter(Boolean).join(' · ');
    }
  } catch (err) {
    // Best-effort, no bloqueante: si falla, se mantiene el nombre de localidad previo.
  }
}

// Búsqueda de dirección/localidad por texto, también vía el backend
async function searchLocality() {
  const input = document.getElementById('map-search-input');
  const query = input.value.trim();
  if (!query) return;

  try {
    const resp = await fetch(`/api/geocode/search?q=${encodeURIComponent(query)}&limit=1`);
    if (!resp.ok) return;
    const results = await resp.json();
    if (results.length === 0) {
      alert('No se encontró esa dirección/localidad en Chile. Prueba con otro texto o haz clic directamente en el mapa.');
      return;
    }

    const { latitude, longitude, display_name, comuna, region_name } = results[0];

    if (state.mapPickerInstance && state.mapPickerMarker) {
      state.mapPickerInstance.setView([latitude, longitude], 13);
      state.mapPickerMarker.setLatLng([latitude, longitude]);
    }

    state.location.latitude = Math.round(latitude * 10000) / 10000;
    state.location.longitude = Math.round(longitude * 10000) / 10000;
    state.location.locality_name = display_name || query;

    document.getElementById('map-locality-name').textContent = display_name || query;
    document.getElementById('map-lat-lon').textContent = `${state.location.latitude.toFixed(4)}° Lat, ${state.location.longitude.toFixed(4)}° Lon`;
    if (comuna || region_name) {
      document.getElementById('map-region-comuna').textContent = [region_name, comuna].filter(Boolean).join(' · ');
    }

    runDimensioning();
  } catch (err) {
    showError(`No se pudo buscar esa dirección. ${friendlyConnectionMessage(err)}`, () => searchLocality());
  }
}

// ================= PASO 3: COMPARATIVA DE 3 OPCIONES (CON BOM Y ENLACES) =================
function renderOptionsComparison(data) {
  const container = document.getElementById('options-comparison-container');
  if (!container) return;
  container.innerHTML = '';

  if (!data.options || data.options.length === 0) {
    renderInlineErrorState('options-comparison-container', 'el servidor no devolvió ninguna opción de sistema', () => runDimensioning());
    return;
  }

  const selectedId = state.preferredOption || 'recomendada';
  data.options.forEach(option => {
    container.appendChild(renderOptionCard(option, option.option_id === selectedId));
  });

  // Siempre hay una opción activa (la recomendada por defecto, o la que el usuario haya
  // elegido), así que continuar nunca debería quedar bloqueado esperando un clic explícito.
  const contBtn = document.getElementById('btn-continue-plano');
  if (contBtn) {
    contBtn.disabled = false;
    const selectedOption = data.options.find(o => o.option_id === selectedId);
    contBtn.textContent = selectedOption
      ? `Continuar con "${selectedOption.label}" →`
      : 'Continuar: Ver Plano de Instalación →';
  }
}

function renderOptionCard(option, isSelected) {
  const card = document.createElement('div');
  card.className = `option-card ${option.is_recommended ? 'is-recommended' : ''} ${isSelected ? 'is-selected' : ''}`;

  const pills = [];
  if (option.is_recommended) pills.push('<span class="option-pill recommended">★ Recomendada por el motor</span>');
  if (isSelected) pills.push('<span class="option-pill selected">✓ Seleccionada</span>');

  const mixLabel = option.system_type === 'HYBRID_SOLAR_WIND' ? 'Híbrido Solar + Eólico' : '100% Solar Fotovoltaico';
  const cardBomId = `bom-list-${option.option_id}`;

  const bomHtml = option.bom.map(item => `
    <div class="bom-line-item">
      <div class="bli-main">
        <span class="bli-name">${item.name}</span>
        <span class="bli-desc">${item.description}</span>
        <span class="bli-qty">${item.quantity} ${item.unit} · ${formatCLP(item.unit_cost_clp)} c/u</span>
      </div>
      <div class="bli-cost">${formatCLP(item.total_cost_clp)}</div>
      ${item.purchase_url ? `<a href="${item.purchase_url}" target="_blank" rel="noopener" class="bom-buy-link">Ver en Mercado Libre ↗</a>` : ''}
    </div>
  `).join('');

  card.innerHTML = `
    <div class="option-card-header">
      <div class="option-card-title">${option.label}</div>
    </div>
    <div>${pills.join(' ')}</div>
    <div class="option-tagline">${option.tagline}</div>
    <div class="option-capex">
      ${formatCLP(option.total_capex_clp)}
      <span class="sub">Inversión Total Estimada (CAPEX) · ~USD $${Math.round(option.total_capex_usd).toLocaleString()}</span>
    </div>
    <div class="option-metrics">
      <div><span>Mezcla</span><b style="font-size:11px;">${mixLabel}</b></div>
      <div><span>Paneles Solares</span><b>${option.num_panels} x 550W</b></div>
      <div><span>Aerogeneradores</span><b>${option.wind_active ? option.turbines_count + ' x 1kW' : '—'}</b></div>
      <div><span>Baterías</span><b>${option.battery_nominal_kwh.toFixed(1)} kWh</b></div>
      <div><span>Retorno Inversión</span><b>${option.simple_payback_years.toFixed(1)} años</b></div>
      <div><span>CO₂ Evitado/año</span><b>${option.annual_co2_avoided_tons.toFixed(2)} Ton</b></div>
    </div>
    <button class="btn-apply-option ${isSelected ? 'selected' : ''}" data-option-id="${option.option_id}">
      ${isSelected ? '✓ Opción Seleccionada' : 'Elegir esta opción'}
    </button>
    <button class="option-bom-toggle" data-target="${cardBomId}">▾ Ver qué comprar y dónde (${option.bom.length} ítems)</button>
    <div class="option-bom-list" id="${cardBomId}">
      ${bomHtml}
      <div class="option-install-row">
        <a href="${option.installation_service_url}" target="_blank" rel="noopener">🔧 Buscador Oficial de Instaladores Certificados SEC ↗</a>
        <a href="${option.sec_installer_registry_url}" target="_blank" rel="noopener">📋 Sitio Oficial SEC (sec.cl) ↗</a>
        <div class="link-disclaimer">Enlaces referenciales de búsqueda; verifica precios, stock y certificación vigente antes de comprar o contratar.</div>
      </div>
    </div>
  `;

  if (!isSelected) {
    card.querySelector('.btn-apply-option').addEventListener('click', () => selectOption(option.option_id));
  }

  card.querySelector('.option-bom-toggle').addEventListener('click', (evt) => {
    const target = document.getElementById(cardBomId);
    const expanded = target.classList.toggle('expanded');
    evt.currentTarget.textContent = expanded
      ? '▴ Ocultar detalle de compra'
      : `▾ Ver qué comprar y dónde (${option.bom.length} ítems)`;
  });

  return card;
}

async function selectOption(optionId) {
  state.preferredOption = optionId;
  await runDimensioning();
  // renderOptionsComparison() (llamada dentro de runDimensioning -> updateUI) ya deja el
  // botón "Continuar" habilitado y actualiza su texto con la opción recién elegida.
}

// ================= PASO 4: PLANO DE INSTALACIÓN (LEAFLET) =================
const EARTH_RADIUS_M = 6371000;

/** Desplaza un punto lat/lon una distancia en metros según un rumbo en grados (0=Norte, 90=Este). */
function offsetLatLon(lat, lon, distanceM, bearingDeg) {
  const bearingRad = (bearingDeg * Math.PI) / 180;
  const latRad = (lat * Math.PI) / 180;
  const dLat = (distanceM * Math.cos(bearingRad)) / EARTH_RADIUS_M;
  const dLon = (distanceM * Math.sin(bearingRad)) / (EARTH_RADIUS_M * Math.cos(latRad));
  return [lat + (dLat * 180) / Math.PI, lon + (dLon * 180) / Math.PI];
}

/** Distancia real en metros entre dos puntos lat/lon (fórmula de Haversine). */
function distanceBetweenM(lat1, lon1, lat2, lon2) {
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a = Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) * Math.cos((lat2 * Math.PI) / 180) * Math.sin(dLon / 2) ** 2;
  return EARTH_RADIUS_M * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

/**
 * Distribuye N viviendas en anillos concéntricos (hasta 8 por anillo, 30m entre anillos),
 * simulando la dispersión real de un caserío rural en vez de amontonarlas siempre cerca
 * del centro. Así, con muchas viviendas o un radio de cobertura chico, el plano muestra
 * honestamente que algunas quedan fuera del alcance práctico de la microrred.
 */
function computeHouseholdPositions(count) {
  const RING_CAPACITY = 8;
  const RING_SPACING_M = 30;
  const positions = [];
  let remaining = count;
  let ring = 0;
  while (remaining > 0) {
    const inThisRing = Math.min(RING_CAPACITY, remaining);
    const radius = RING_SPACING_M * (ring + 1);
    for (let i = 0; i < inThisRing; i++) {
      const bearing = (360 / inThisRing) * i + ring * 15;
      positions.push({ radius, bearing });
    }
    remaining -= inThisRing;
    ring++;
  }
  return positions;
}

const ZONE_COLORS = {
  'Arreglo Fotovoltaico': '#c08516',
  'Microturbina Eólica': '#0891b2',
  'Banco de Baterías + Inversor': '#059669'
};

const ZONE_ICONS = {
  'Arreglo Fotovoltaico': '☀️',
  'Microturbina Eólica': '🌀',
  'Banco de Baterías + Inversor': '🔋'
};

function setupMapLayout(lat, lon) {
  const el = document.getElementById('map-layout');
  if (!el) return null;
  if (typeof L === 'undefined') {
    showError('No se pudo inicializar el plano de instalación: la librería Leaflet no cargó (revisa tu conexión a internet).');
    return null;
  }

  if (!state.mapLayoutInstance) {
    const map = L.map('map-layout', { zoomControl: true }).setView([lat, lon], 17);
    addTileLayerWithErrorHandling(map, 'plano de instalación');
    state.mapLayoutInstance = map;
    state.mapLayoutLayerGroup = L.layerGroup().addTo(map);
  } else {
    state.mapLayoutInstance.setView([lat, lon], 17);
    state.mapLayoutLayerGroup.clearLayers();
  }
  return state.mapLayoutInstance;
}

function makeEmojiDivIcon(emoji, extraClass, size) {
  return L.divIcon({
    className: '',
    html: `<div class="enchufate-map-icon ${extraClass || ''}" style="font-size:${size || 20}px;">${emoji}</div>`,
    iconSize: [size || 24, size || 24],
    iconAnchor: [(size || 24) / 2, (size || 24) / 2]
  });
}

function renderInstallationLayout(data) {
  const layout = data.site_layout;
  const map = setupMapLayout(data.location.latitude, data.location.longitude);
  if (!map || !layout) return;

  const group = state.mapLayoutLayerGroup;
  const centerLat = data.location.latitude;
  const centerLon = data.location.longitude;

  document.getElementById('plano-households-badge').textContent =
    `${layout.households_count} ${layout.households_count === 1 ? 'vivienda' : 'viviendas'}`;

  // Punto real del gabinete de baterías/inversor: es el origen de la red de distribución AC,
  // por lo que el radio de cobertura se mide desde ahí (no desde el centro genérico del predio).
  const bZone = layout.battery_zone;
  const bMidDist = (bZone.min_distance_m + bZone.max_distance_m) / 2;
  const [hubLat, hubLon] = offsetLatLon(centerLat, centerLon, Math.max(bMidDist, 1), bZone.bearing_deg);

  // -------- Círculo de cobertura práctica (opaco/semi-transparente) --------
  L.circle([hubLat, hubLon], {
    radius: layout.coverage_radius_m,
    color: '#0e6151',
    weight: 2,
    dashArray: '8,6',
    fillColor: '#0e6151',
    fillOpacity: 0.14
  }).addTo(group).bindPopup(
    `<b>Radio de cobertura práctico: ≈${layout.coverage_radius_m.toFixed(0)} m</b><br>` +
    'Dentro de este radio, el cableado AC llega sin caídas de tensión relevantes. ' +
    'Viviendas fuera de este círculo pueden necesitar cableado reforzado, un segundo hub, o sistema propio.'
  );

  // -------- Viviendas (en anillos realistas, no todas amontonadas en el centro) --------
  const positions = computeHouseholdPositions(layout.households_count);
  let coveredCount = 0;
  positions.forEach((pos, i) => {
    const [hLat, hLon] = offsetLatLon(centerLat, centerLon, pos.radius, pos.bearing);
    const distToHub = distanceBetweenM(hubLat, hubLon, hLat, hLon);
    const isCovered = distToHub <= layout.coverage_radius_m;
    if (isCovered) coveredCount++;

    const icon = makeEmojiDivIcon('🏠', isCovered ? 'house-covered' : 'house-not-covered', 22);
    const popupText = isCovered
      ? `Vivienda ${i + 1} · ≈${distToHub.toFixed(0)} m del hub · ✅ dentro del radio de cobertura`
      : `Vivienda ${i + 1} · ≈${distToHub.toFixed(0)} m del hub · ⚠️ FUERA del radio de cobertura práctico`;
    L.marker([hLat, hLon], { icon }).addTo(group).bindPopup(popupText);
  });

  const notCoveredCount = layout.households_count - coveredCount;

  // -------- Zonas de equipos: círculo semi-transparente (área) + marcador emoji (ubicación exacta) --------
  const zones = [layout.solar_zone, layout.wind_zone, layout.battery_zone].filter(Boolean);
  const legendContainer = document.getElementById('layout-legend-container');
  legendContainer.innerHTML = '';

  zones.forEach(zone => {
    const midDistance = (zone.min_distance_m + zone.max_distance_m) / 2;
    const [zLat, zLon] = offsetLatLon(centerLat, centerLon, Math.max(midDistance, 3), zone.bearing_deg);
    const color = ZONE_COLORS[zone.equipment] || '#0e6151';
    const radius = Math.max(4, (zone.max_distance_m - zone.min_distance_m) / 2 + 3);
    const emoji = ZONE_ICONS[zone.equipment] || '📍';

    L.circle([zLat, zLon], {
      radius,
      color,
      weight: 2,
      fillColor: color,
      fillOpacity: 0.3
    }).addTo(group).bindPopup(`<b>${emoji} ${zone.equipment}</b><br>${zone.note}`);

    L.marker([zLat, zLon], { icon: makeEmojiDivIcon(emoji, 'zone-icon', 22) }).addTo(group)
      .bindPopup(`<b>${emoji} ${zone.equipment}</b><br>${zone.note}`);

    L.polyline([[centerLat, centerLon], [zLat, zLon]], {
      color, weight: 1.5, dashArray: '4,4', opacity: 0.7
    }).addTo(group);

    const legendItem = document.createElement('div');
    legendItem.className = 'layout-legend-item';
    legendItem.innerHTML = `
      <div class="legend-title"><span class="legend-swatch" style="background:${color}"></span>${emoji} ${zone.equipment}</div>
      <div class="legend-detail">${zone.direction} · ${zone.min_distance_m.toFixed(0)}-${zone.max_distance_m.toFixed(0)} m de la vivienda · ≈${zone.area_m2} m²</div>
    `;
    legendContainer.appendChild(legendItem);
  });

  // -------- Resumen de cobertura (llamativo si hay viviendas sin cubrir) --------
  const coverageBanner = document.getElementById('layout-coverage-banner');
  if (notCoveredCount > 0) {
    coverageBanner.className = 'layout-coverage-banner warning';
    coverageBanner.innerHTML = `⚠️ <b>${notCoveredCount} de ${layout.households_count}</b> vivienda(s) quedan fuera del radio práctico ` +
      `de cobertura (≈${layout.coverage_radius_m.toFixed(0)} m). Considera un segundo hub de generación, cableado reforzado, o un sistema propio para esas viviendas.`;
  } else {
    coverageBanner.className = 'layout-coverage-banner ok';
    coverageBanner.innerHTML = `✅ Las <b>${layout.households_count}</b> vivienda(s) quedan dentro del radio práctico de cobertura (≈${layout.coverage_radius_m.toFixed(0)} m).`;
  }

  const notesContainer = document.getElementById('layout-notes-container');
  notesContainer.innerHTML = '';
  layout.general_notes.forEach(note => {
    const li = document.createElement('li');
    li.textContent = note;
    notesContainer.appendChild(li);
  });

  setTimeout(() => map.invalidateSize(), 50);
}

// ================= PASO 5: EXPEDIENTE TE1 SEC (memoria + checklist + diagrama) =================
function renderSecChecklist(checklist) {
  const container = document.getElementById('sec-checklist-container');
  container.innerHTML = '';
  checklist.forEach(item => {
    const card = document.createElement('div');
    card.className = 'sec-check-card';
    card.innerHTML = `
      <div class="sec-check-header">
        <span class="sec-norm-title">${item.norm}</span>
        <span class="sec-status-pill">✓ Cumple Diseño</span>
      </div>
      <div class="sec-req-text">${item.requirement}</div>
      <div class="sec-det-text">${item.details}</div>
    `;
    container.appendChild(card);
  });
}

function updateTe1Tab(data) {
  const loc = data.location;
  const demand = data.demand;
  const solar = data.solar;
  const bat = data.battery;
  const inv = data.inverter;

  document.getElementById('te1-proj-name').textContent = `EnchufaTE Off-Grid (${loc.locality_name || 'Predio Rural'})`;
  document.getElementById('te1-region-name').textContent = loc.locality_name || (loc.region_id ? loc.region_id.toUpperCase() : 'Chile');
  document.getElementById('te1-coords').textContent = `${loc.latitude.toFixed(4)}° Lat, ${loc.longitude.toFixed(4)}° Lon`;

  document.getElementById('te1-energy-daily').textContent = `${demand.total_daily_kwh.toFixed(2)} kWh/día`;
  document.getElementById('te1-energy-annual').textContent = `${Math.round(demand.total_annual_kwh).toLocaleString()} kWh/año`;
  document.getElementById('te1-power-peak').textContent = `${(demand.peak_synchronous_power_w / 1000).toFixed(2)} kW`;
  document.getElementById('te1-power-surge').textContent = `${(demand.peak_surge_power_w / 1000).toFixed(2)} kW`;

  document.getElementById('te1-pv-installed').textContent = `${solar.installed_pv_kwp.toFixed(2)} kWp (${solar.num_panels} módulos 550Wp)`;
  document.getElementById('te1-tilt-azimuth').textContent = `${solar.optimal_tilt_deg}° Tilt / 0° Norte`;
  document.getElementById('te1-bat-capacity').textContent = `${bat.nominal_capacity_kwh.toFixed(1)} kWh nominal / ${bat.usable_capacity_kwh.toFixed(1)} kWh útil`;
  document.getElementById('te1-inv-rating').textContent = `${inv.nominal_power_kva.toFixed(1)} kVA 48V Onda Pura`;

  document.getElementById('diag-pv-desc').textContent = `${solar.num_panels}x 550Wp (${solar.installed_pv_kwp.toFixed(2)} kWp)`;
  document.getElementById('diag-inv-desc').textContent = `${inv.nominal_power_kva.toFixed(1)} kVA 48V MPPT`;
  document.getElementById('diag-bat-desc').textContent = `${bat.num_modules}x ${bat.module_kwh.toFixed(1)} kWh = ${bat.nominal_capacity_kwh.toFixed(1)} kWh`;

  const docsContainer = document.getElementById('te1-docs-container');
  docsContainer.innerHTML = '';
  data.sec_compliance.te1_requirements.forEach(req => {
    const li = document.createElement('li');
    li.textContent = req;
    docsContainer.appendChild(li);
  });
}

// ================= MODAL DE CARGA PERSONALIZADA =================
function setupModal() {
  const modal = document.getElementById('modal-custom-appliance');
  const btnOpen = document.getElementById('btn-add-custom-appliance');
  const btnClose = document.getElementById('btn-close-modal');
  const btnCancel = document.getElementById('btn-cancel-custom');
  const btnSave = document.getElementById('btn-save-custom');

  btnOpen.addEventListener('click', () => {
    modal.classList.remove('hidden');
  });

  const closeModal = () => modal.classList.add('hidden');
  btnClose.addEventListener('click', closeModal);
  btnCancel.addEventListener('click', closeModal);

  btnSave.addEventListener('click', () => {
    const name = document.getElementById('custom-app-name').value.trim() || 'Equipo Adicional';
    const power = parseFloat(document.getElementById('custom-app-power').value) || 150;
    const hours = parseFloat(document.getElementById('custom-app-hours').value) || 2;
    const qty = parseInt(document.getElementById('custom-app-qty').value, 10) || 1;
    const surge = parseFloat(document.getElementById('custom-app-surge').value) || 1.0;

    const newItem = {
      id: `custom_${Date.now()}`,
      name: name,
      category: 'personalizado',
      power_w: power,
      hours_per_day: hours,
      quantity: qty,
      surge_multiplier: surge,
      duty_cycle: 1.0,
      enabled: true
    };

    state.appliances.push(newItem);
    renderAppliancesList();
    runDimensioning();
    closeModal();
  });
}

// ================= UTILIDADES =================
function formatCLP(val) {
  return `$${Math.round(val).toLocaleString('es-CL')} CLP`;
}

/**
 * Escapa HTML antes de insertar texto potencialmente controlado por el usuario (nombre de
 * artefacto personalizado, mensajes de error que pueden reflejar datos de una petición
 * inválida, etc.) dentro de innerHTML, para prevenir XSS.
 */
function escapeHtml(value) {
  if (value === null || value === undefined) return '';
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}
