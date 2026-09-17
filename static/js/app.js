const socket = io();

const el = {
  lightIndicator: document.getElementById("lightIndicator"),
  secondsInState: document.getElementById("secondsInState"),
  greenTarget: document.getElementById("greenTarget"),
  totalVehicles: document.getElementById("totalVehicles"),
  movingVehicles: document.getElementById("movingVehicles"),
  stoppedVehicles: document.getElementById("stoppedVehicles"),
  emergencyBadge: document.getElementById("emergencyBadge"),
  emergencyConfidence: document.getElementById("emergencyConfidence"),
  headlightState: document.getElementById("headlightState"),
  cameraSource: document.getElementById("cameraSource"),
  audioEnabled: document.getElementById("audioEnabled"),
  hardwareAvailable: document.getElementById("hardwareAvailable"),
  sourceInput: document.getElementById("sourceInput"),
  applySource: document.getElementById("applySource"),
  audioToggle: document.getElementById("audioToggle"),
  manualModeToggle: document.getElementById("manualModeToggle"),
  manualCars: document.getElementById("manualCars"),
  manualMotorcycles: document.getElementById("manualMotorcycles"),
  carMinus: document.getElementById("carMinus"),
  carPlus: document.getElementById("carPlus"),
  motorcycleMinus: document.getElementById("motorcycleMinus"),
  motorcyclePlus: document.getElementById("motorcyclePlus"),
  ambulanceToggle: document.getElementById("ambulanceToggle"),
  sirenToggle: document.getElementById("sirenToggle"),
};

const simulationState = {
  enabled: false,
  cars: 0,
  motorcycles: 0,
  ambulance: false,
  siren: false,
};

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function updateSimulationUI() {
  if (!el.manualModeToggle) return;

  el.manualModeToggle.checked = simulationState.enabled;
  if (el.manualCars) el.manualCars.textContent = simulationState.cars;
  if (el.manualMotorcycles) el.manualMotorcycles.textContent = simulationState.motorcycles;

  const controlsDisabled = !simulationState.enabled;
  [
    el.carMinus,
    el.carPlus,
    el.motorcycleMinus,
    el.motorcyclePlus,
    el.ambulanceToggle,
    el.sirenToggle,
  ].filter(Boolean).forEach((button) => {
    button.disabled = controlsDisabled;
  });

  if (el.ambulanceToggle) {
    el.ambulanceToggle.classList.toggle("active", simulationState.ambulance);
  }
  if (el.sirenToggle) {
    el.sirenToggle.classList.toggle("active", simulationState.siren);
  }
}

async function pushSimulationState() {
  const res = await fetch("/api/simulation", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(simulationState),
  });
  const payload = await res.json();
  simulationState.enabled = !!payload.enabled;
  simulationState.cars = Number(payload.cars) || 0;
  simulationState.motorcycles = Number(payload.motorcycles) || 0;
  simulationState.ambulance = !!payload.ambulance;
  simulationState.siren = !!payload.siren;
  updateSimulationUI();
}

function renderStatus(data) {
  el.lightIndicator.textContent = data.light === "GREEN" ? "VERDE" : "VERMELHO";
  el.lightIndicator.className = "light-indicator " + (data.light === "GREEN" ? "green" : "red");

  el.secondsInState.textContent = data.seconds_in_state ?? "-";
  el.greenTarget.textContent = data.green_time_target ?? "-";
  el.totalVehicles.textContent = data.total_vehicles ?? 0;
  el.movingVehicles.textContent = data.moving_vehicles ?? 0;
  el.stoppedVehicles.textContent = data.stopped_vehicles ?? 0;

  if (data.emergency_active) {
    el.emergencyBadge.textContent = "🚨 VEÍCULO DE EMERGÊNCIA DETECTADO";
    el.emergencyBadge.className = "badge active";
  } else {
    el.emergencyBadge.textContent = "Nenhum detectado";
    el.emergencyBadge.className = "badge inactive";
  }

  el.emergencyConfidence.textContent = Math.round((data.emergency_confidence || 0) * 100) + "%";
  el.headlightState.textContent = data.headlight_on ? "Sim" : "Não";
  el.cameraSource.textContent = data.camera_source ?? "-";
  el.audioEnabled.textContent = data.audio_enabled ? "Sim" : "Não";
  el.hardwareAvailable.textContent = data.hardware_available ? "Real (GPIO)" : "Simulado";

  if (typeof data.manual_mode === "boolean") {
    simulationState.enabled = data.manual_mode;
    simulationState.cars = Number(data.manual_cars) || 0;
    simulationState.motorcycles = Number(data.manual_motorcycles) || 0;
    simulationState.ambulance = !!data.manual_ambulance;
    simulationState.siren = !!data.manual_siren;
    updateSimulationUI();
  }
}

socket.on("status_update", renderStatus);

// fallback via polling caso o websocket não conecte
setInterval(async () => {
  if (socket.connected) return;
  try {
    const res = await fetch("/api/status");
    const data = await res.json();
    renderStatus(data);
  } catch (e) { /* ignora */ }
}, 1000);

el.applySource.addEventListener("click", async () => {
  const source = el.sourceInput.value.trim();
  await fetch("/api/source", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ source }),
  });
});

el.audioToggle.addEventListener("change", async () => {
  await fetch("/api/audio", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enable: el.audioToggle.checked }),
  });
});

if (el.manualModeToggle) {
  el.manualModeToggle.addEventListener("change", async () => {
    simulationState.enabled = el.manualModeToggle.checked;
    await pushSimulationState();
  });
}

if (el.carMinus) {
  el.carMinus.addEventListener("click", async () => {
    simulationState.cars = clamp(simulationState.cars - 1, 0, 200);
    await pushSimulationState();
  });
}

if (el.carPlus) {
  el.carPlus.addEventListener("click", async () => {
    simulationState.cars = clamp(simulationState.cars + 1, 0, 200);
    await pushSimulationState();
  });
}

if (el.motorcycleMinus) {
  el.motorcycleMinus.addEventListener("click", async () => {
    simulationState.motorcycles = clamp(simulationState.motorcycles - 1, 0, 200);
    await pushSimulationState();
  });
}

if (el.motorcyclePlus) {
  el.motorcyclePlus.addEventListener("click", async () => {
    simulationState.motorcycles = clamp(simulationState.motorcycles + 1, 0, 200);
    await pushSimulationState();
  });
}

if (el.ambulanceToggle) {
  el.ambulanceToggle.addEventListener("click", async () => {
    simulationState.ambulance = !simulationState.ambulance;
    await pushSimulationState();
  });
}

if (el.sirenToggle) {
  el.sirenToggle.addEventListener("click", async () => {
    simulationState.siren = !simulationState.siren;
    await pushSimulationState();
  });
}

updateSimulationUI();
