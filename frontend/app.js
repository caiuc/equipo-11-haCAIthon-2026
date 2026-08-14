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

function showError(message) {
  console.error(message);
  const banner = document.getElementById('error-banner');
  const text = document.getElementById('error-banner-text');
  if (!banner || !text) {
    alert(message);
    return;
  }
  text.textContent = message;
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

// Inicialización
document.addEventListener('DOMContentLoaded', async () => {
  setupErrorBanner();
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
    }

    // Catálogo Base de Artefactos
    const resCat = await fetch('/api/catalogo');
    if (resCat.ok) {
      const catalog = await resCat.json();
      state.appliances = catalog.map(item => ({
        ...item,
        enabled: item.id === 'refrigerador_inverter' || item.id === 'starlink_internet' ||
                 item.id === 'bomba_agua_05hp' || item.id === 'iluminacion_led_rural' ||
                 item.id === 'cargadores_dispositivos' || item.id === 'televisor_smart_led'
      }));
      renderAppliancesList();
    }
  } catch (err) {
    console.warn('Error cargando catálogo desde API, usando defaults locales:', err);
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
          <div class="appliance-title">${app.name}</div>
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
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();
    state.lastResult = data;
    updateUI(data);
  } catch (err) {
    console.error('Error calculando dimensionamiento:', err);
  }
}

// ================= ACTUALIZAR TODA LA INTERFAZ =================
function updateUI(data) {
  // -------- Paso 1: Clima y Ubicación --------
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

  // -------- Paso 2: Demanda --------
  const demand = data.demand;
  document.getElementById('badge-total-kwh').textContent = `${demand.total_daily_kwh.toFixed(2)} kWh/día`;
  document.getElementById('val-peak-power').textContent = `${(demand.peak_synchronous_power_w / 1000).toFixed(2)} kW`;
  document.getElementById('val-surge-power').textContent = `${(demand.peak_surge_power_w / 1000).toFixed(2)} kW`;

  // -------- Paso 3: Comparativa de 3 Opciones --------
  renderOptionsComparison(data);

  // -------- Paso 4: Plano de Instalación --------
  renderInstallationLayout(data);

  // -------- Paso 5: Expediente TE1 SEC (memoria + checklist + diagrama) --------
  updateTe1Tab(data);
  renderSecChecklist(data.sec_compliance.checklist);
}

// ================= PASO 1: MAPA / UBICACIÓN (LEAFLET) =================
function setupMapPicker() {
  const el = document.getElementById('map-picker');
  if (!el || typeof L === 'undefined') return;

  const map = L.map('map-picker', { zoomControl: true }).setView([state.location.latitude, state.location.longitude], 11);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors',
    maxZoom: 18
  }).addTo(map);

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
    console.warn('Error buscando localidad:', err);
  }
}

// ================= PASO 3: COMPARATIVA DE 3 OPCIONES (CON BOM Y ENLACES) =================
function renderOptionsComparison(data) {
  const container = document.getElementById('options-comparison-container');
  if (!container) return;
  container.innerHTML = '';

  const selectedId = state.preferredOption || 'recomendada';
  data.options.forEach(option => {
    container.appendChild(renderOptionCard(option, option.option_id === selectedId));
  });
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
        <span class="bli-desc">${item.description}</span>
        <span class="bli-qty">${item.quantity} ${item.unit} · ${formatCLP(item.unit_cost_clp)} c/u</span>
      </div>
      <div class="bli-cost">${formatCLP(item.total_cost_clp)}</div>
      ${item.purchase_url ? `<a href="${item.purchase_url}" target="_blank" rel="noopener" class="bom-buy-link">Dónde comprar ↗</a>` : ''}
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
        <a href="${option.installation_service_url}" target="_blank" rel="noopener">🔧 Buscar instalador certificado SEC cerca de ti ↗</a>
        <a href="${option.sec_installer_registry_url}" target="_blank" rel="noopener">📋 Registro oficial de instaladores SEC (sec.cl) ↗</a>
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
  const contBtn = document.getElementById('btn-continue-plano');
  contBtn.disabled = false;
  contBtn.textContent = 'Continuar: Ver Plano de Instalación →';
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

const ZONE_COLORS = {
  'Arreglo Fotovoltaico': '#d97706',
  'Microturbina Eólica': '#0891b2',
  'Banco de Baterías + Inversor': '#059669'
};

function setupMapLayout(lat, lon) {
  const el = document.getElementById('map-layout');
  if (!el || typeof L === 'undefined') return null;

  if (!state.mapLayoutInstance) {
    const map = L.map('map-layout', { zoomControl: true }).setView([lat, lon], 17);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors',
      maxZoom: 19
    }).addTo(map);
    state.mapLayoutInstance = map;
    state.mapLayoutLayerGroup = L.layerGroup().addTo(map);
  } else {
    state.mapLayoutInstance.setView([lat, lon], 17);
    state.mapLayoutLayerGroup.clearLayers();
  }
  return state.mapLayoutInstance;
}

function renderInstallationLayout(data) {
  const layout = data.site_layout;
  const map = setupMapLayout(data.location.latitude, data.location.longitude);
  if (!map || !layout) return;

  const group = state.mapLayoutLayerGroup;
  const centerLat = data.location.latitude;
  const centerLon = data.location.longitude;
  const houseIcon = L.divIcon({ className: '', html: '<div class="enchufate-house-icon">🏠</div>', iconSize: [22, 22], iconAnchor: [11, 11] });

  document.getElementById('plano-households-badge').textContent =
    `${layout.households_count} ${layout.households_count === 1 ? 'vivienda' : 'viviendas'}`;

  const householdsToDraw = Math.min(layout.households_count, 8);
  if (householdsToDraw === 1) {
    L.marker([centerLat, centerLon], { icon: houseIcon }).addTo(group).bindPopup('Vivienda');
  } else {
    for (let i = 0; i < householdsToDraw; i++) {
      const bearing = (360 / householdsToDraw) * i;
      const [hLat, hLon] = offsetLatLon(centerLat, centerLon, 12, bearing);
      L.marker([hLat, hLon], { icon: houseIcon }).addTo(group).bindPopup(`Vivienda ${i + 1}`);
    }
    if (layout.households_count > householdsToDraw) {
      L.marker([centerLat, centerLon], { icon: houseIcon }).addTo(group)
        .bindPopup(`+${layout.households_count - householdsToDraw} viviendas adicionales (caserío)`);
    }
  }

  const zones = [layout.solar_zone, layout.wind_zone, layout.battery_zone].filter(Boolean);
  const legendContainer = document.getElementById('layout-legend-container');
  legendContainer.innerHTML = '';

  zones.forEach(zone => {
    const midDistance = (zone.min_distance_m + zone.max_distance_m) / 2;
    const [zLat, zLon] = offsetLatLon(centerLat, centerLon, Math.max(midDistance, 3), zone.bearing_deg);
    const color = ZONE_COLORS[zone.equipment] || '#0284c7';
    const radius = Math.max(4, (zone.max_distance_m - zone.min_distance_m) / 2 + 3);

    L.circle([zLat, zLon], {
      radius,
      color,
      weight: 2,
      fillColor: color,
      fillOpacity: 0.25
    }).addTo(group).bindPopup(`<b>${zone.equipment}</b><br>${zone.note}`);

    L.polyline([[centerLat, centerLon], [zLat, zLon]], {
      color, weight: 1.5, dashArray: '4,4', opacity: 0.7
    }).addTo(group);

    const legendItem = document.createElement('div');
    legendItem.className = 'layout-legend-item';
    legendItem.innerHTML = `
      <div class="legend-title"><span class="legend-swatch" style="background:${color}"></span>${zone.equipment}</div>
      <div class="legend-detail">${zone.direction} · ${zone.min_distance_m.toFixed(0)}-${zone.max_distance_m.toFixed(0)} m de la vivienda · ≈${zone.area_m2} m²</div>
    `;
    legendContainer.appendChild(legendItem);
  });

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
