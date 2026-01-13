document.addEventListener('DOMContentLoaded', () => {
    const video = document.getElementById('videoFeed');
    const canvas = document.getElementById('roiCanvas');
    const ctx = canvas.getContext('2d');
    const videoContainer = document.getElementById('videoContainer');

    // UI Elements
    const btnAddZone = document.getElementById('btnAddZone');
    const btnClearZones = document.getElementById('btnClearZones');
    const btnToggleAway = document.getElementById('btnToggleAway');
    const zoneList = document.getElementById('zoneList');
    const zoneCount = document.getElementById('zoneCount');

    const alertBanner = document.getElementById('alertBanner');
    const btnDismiss = document.getElementById('btnDismiss');
    const btnDanger = document.getElementById('btnDanger');

    const systemStatusPill = document.getElementById('systemStatusPill');
    const statusTextPill = document.getElementById('statusTextPill');

    // State
    let isDrawingMode = false;
    let isDrawing = false;
    let startX, startY, endX, endY;
    let awayMode = false;
    let zones = [];

    // Resize canvas
    function resizeCanvas() {
        canvas.width = video.clientWidth;
        canvas.height = video.clientHeight;
        drawAllZones();
    }
    window.addEventListener('resize', resizeCanvas);
    video.onload = resizeCanvas;
    // Periodic resize check in case video loads late
    setInterval(resizeCanvas, 2000);

    // --- Inputs & Controls ---

    // Initial state fetch
    async function init() {
        refreshZones();
        const status = await getStatus();
        if (status) {
            awayMode = status.away_mode;
            updateUIState(awayMode);
        }
    }
    init();

    // --- Zone Management ---

    btnAddZone.addEventListener('click', () => {
        isDrawingMode = !isDrawingMode;
        if (isDrawingMode) {
            videoContainer.classList.add('selecting');
            videoContainer.style.cursor = "crosshair";
            btnAddZone.innerHTML = '<i class="fa-solid fa-xmark"></i> Cancel';
            btnAddZone.classList.add('active');
        } else {
            videoContainer.classList.remove('selecting');
            videoContainer.style.cursor = "default";
            btnAddZone.innerHTML = '<i class="fa-solid fa-plus"></i> Add Zone';
            btnAddZone.classList.remove('active');
        }
    });

    // Drawing Logic (Mouse & Touch)
    function getPointerPos(e) {
        const rect = canvas.getBoundingClientRect();
        // Check if touch event
        if (e.touches && e.touches.length > 0) {
            return {
                x: e.touches[0].clientX - rect.left,
                y: e.touches[0].clientY - rect.top
            };
        } else if (e.changedTouches && e.changedTouches.length > 0) {
            return {
                x: e.changedTouches[0].clientX - rect.left,
                y: e.changedTouches[0].clientY - rect.top
            };
        }
        // Mouse event
        return {
            x: e.clientX - rect.left,
            y: e.clientY - rect.top
        };
    }

    function handleStart(e) {
        if (!isDrawingMode) return;
        e.preventDefault(); // Prevent scrolling on mobile
        isDrawing = true;
        const pos = getPointerPos(e);
        startX = pos.x;
        startY = pos.y;
    }

    function handleMove(e) {
        if (!isDrawingMode || !isDrawing) return;
        e.preventDefault();
        const pos = getPointerPos(e);
        endX = pos.x;
        endY = pos.y;

        drawAllZones(); // Keep existing
        // Draw current draft
        ctx.strokeStyle = '#3b82f6';
        ctx.lineWidth = 2;
        ctx.setLineDash([5, 3]);
        ctx.strokeRect(startX, startY, endX - startX, endY - startY);
        ctx.setLineDash([]);
    }

    async function handleEnd(e) {
        if (!isDrawingMode || !isDrawing) return;
        e.preventDefault();
        isDrawing = false;

        let w = Math.abs(endX - startX);
        let h = Math.abs(endY - startY);
        let x = Math.min(startX, endX);
        let y = Math.min(startY, endY);

        if (w > 20 && h > 20) {
            // Persist
            const zoneName = `Zone ${zones.length + 1}`;
            await addZone(x, y, w, h, zoneName);

            // Exit drawing mode
            isDrawingMode = false;
            videoContainer.classList.remove('selecting');
            videoContainer.style.cursor = "default";
            btnAddZone.innerHTML = '<i class="fa-solid fa-plus"></i> Add Zone';
            btnAddZone.classList.remove('active');
        } else {
            drawAllZones(); // Clear partial
        }
    }

    canvas.addEventListener('mousedown', handleStart);
    canvas.addEventListener('touchstart', handleStart, { passive: false });

    canvas.addEventListener('mousemove', handleMove);
    canvas.addEventListener('touchmove', handleMove, { passive: false });

    canvas.addEventListener('mouseup', handleEnd);
    canvas.addEventListener('touchend', handleEnd, { passive: false });

    async function addZone(x, y, w, h, name) {
        const scaleX = video.naturalWidth / video.clientWidth;
        const scaleY = video.naturalHeight / video.clientHeight;

        try {
            const response = await fetch('/api/set_roi', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    x: Math.round(x * scaleX),
                    y: Math.round(y * scaleY),
                    w: Math.round(w * scaleX),
                    h: Math.round(h * scaleY),
                    name: name
                })
            });
            await refreshZones();
        } catch (e) { console.error(e); }
    }

    window.deleteZone = async function (id) {
        // Removed confirmation per user request
        try {
            await fetch('/api/delete_roi', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id: id })
            });
            await refreshZones();
        } catch (e) { console.error(e); }
    };

    async function refreshZones() {
        try {
            const res = await fetch('/api/get_rois');
            zones = await res.json();
            renderZoneList();
            drawAllZones();
        } catch (e) { console.error(e); }
    }

    function renderZoneList() {
        zoneCount.textContent = zones.length;
        if (zones.length === 0) {
            zoneList.innerHTML = '<li class="empty-state">No zones defined. Add a zone to start monitoring.</li>';
            return;
        }

        zoneList.innerHTML = zones.map(z => `
            <li class="zone-item">
                <span><i class="fa-regular fa-square" style="color: #3b82f6"></i> ${z.name}</span>
                <button onclick="deleteZone('${z.id}')" class="btn-icon danger" title="Remove"><i class="fa-solid fa-xmark"></i></button>
            </li>
        `).join('');
    }

    function drawAllZones() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // Scale back from video source to display
        const scaleX = video.clientWidth / video.naturalWidth;
        const scaleY = video.clientHeight / video.naturalHeight;

        zones.forEach(z => {
            const [zx, zy, zw, zh] = z.rect;
            const x = zx * scaleX;
            const y = zy * scaleY;
            const w = zw * scaleX;
            const h = zh * scaleY;

            ctx.strokeStyle = '#3b82f6';
            ctx.lineWidth = 2;
            ctx.strokeRect(x, y, w, h);
            ctx.fillStyle = 'rgba(59, 130, 246, 0.1)';
            ctx.fillRect(x, y, w, h);

            ctx.fillStyle = '#3b82f6';
            ctx.font = "12px sans-serif";
            ctx.fillText(z.name, x, y - 5);
        });
    }

    // --- System Control ---

    function updateButtonState(btn, isActive, inactiveText, activeText, inactiveClass, activeClass) {
        if (isActive) {
            btn.innerHTML = `<i class="fa-solid fa-stop"></i> ${activeText}`;
            if (activeClass) btn.classList.add(activeClass);
            if (inactiveClass) btn.classList.remove(inactiveClass);
            // Specific overrides
            if (activeClass === 'btn-secondary-active') {
                btn.style.backgroundColor = "#4834d4";
                btn.style.color = "white";
            }
        } else {
            btn.innerHTML = `<i class="fa-solid fa-play"></i> ${inactiveText}`;
            if (activeClass) btn.classList.remove(activeClass);
            if (inactiveClass) btn.classList.add(inactiveClass);
            if (activeClass === 'btn-secondary-active') {
                btn.style.backgroundColor = "";
                btn.style.color = "";
            }
        }
    }

    async function toggleFeature(url, status) {
        try {
            await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: status })
            });
            // State will be updated by polling
        } catch (e) { console.error(e); }
    }

    // --- System Control ---

    btnToggleAway.addEventListener('click', () => {
        // Toggle happens via polling update, but we send the request
        toggleFeature('/api/toggle_away', !awayMode);
    });

    const btnToggleNight = document.getElementById('btnToggleNight');
    // Removed local nightModeEnabled, rely on polling data

    btnToggleNight.addEventListener('click', () => {
        // We need current state to toggle
        // We will read from the button state or a global var updated by poll
        // For simplicity, let's just trigger the inverse of what we last saw in poll
        // BUT, since we don't have the var easily accessible here without race conditions,
        // let's just use the visual state or better yet, store state globally.
        // See 'init' and polling.
    });
    // Re-implement listeners properly using global state updated by poll

    // We already have 'awayMode' global. Let's add others.
    let nightModeEnabled = false;
    let weaponCheckEnabled = false;

    btnToggleNight.addEventListener('click', () => {
        toggleFeature('/api/toggle_night_mode', !nightModeEnabled);
    });

    const btnToggleWeapon = document.getElementById('btnToggleWeapon');
    if (btnToggleWeapon) {
        btnToggleWeapon.addEventListener('click', () => {
            toggleFeature('/api/toggle_weapon_detection', !weaponCheckEnabled);
        });
    }

    // Update UI Helper (Legacy removed, replaced by updateButtonState in poll)
    // ...

    // --- Polling ---
    async function getStatus() {
        try {
            const res = await fetch('/api/status');
            return await res.json();
        } catch (e) { return null; }
    }

    setInterval(async () => {
        const status = await getStatus();
        if (!status) return;

        // Sync State Variables (CRITICAL for button logic)
        awayMode = status.away_mode;
        nightModeEnabled = status.night_mode_enabled;
        weaponCheckEnabled = status.weapon_check_enabled;

        // Update Button States
        updateButtonState(btnToggleAway, status.away_mode, 'Start Away Mode', 'Stop Away Mode', 'btn-primary', 'btn-danger');
        updateButtonState(btnToggleNight, status.night_mode_enabled, 'Enable Night Mode', 'Disable Night Mode', 'btn-secondary', 'btn-secondary-active');
        if (btnToggleWeapon) {
            updateButtonState(btnToggleWeapon, status.weapon_check_enabled, 'Enable Weapon Detection', 'Disable Weapon Detection', 'btn-secondary', 'btn-danger'); // Red for danger
        }

        if (status.alarm_active) {
            alertBanner.classList.remove('hidden');
            systemStatusPill.classList.add('alarm');
            statusTextPill.textContent = "INTRUDER ALERT";
            document.querySelector('.alert-info h2').textContent = "INTRUDER DETECTED";
            document.querySelector('.alert-info p').textContent = "Person detected in restricted zone!";
            // Reset styles
            alertBanner.style.backgroundColor = "";
            alertBanner.style.borderColor = "";
        } else if (status.weapon_active) {
            alertBanner.classList.remove('hidden');
            systemStatusPill.classList.add('alarm');
            // Critical Red Styles
            alertBanner.style.backgroundColor = "rgba(255, 0, 0, 0.2)";
            alertBanner.style.borderColor = "#ff0000";
            statusTextPill.textContent = "CRITICAL THREAT";
            document.querySelector('.alert-info h2').textContent = "WEAPON DETECTED";
            document.querySelector('.alert-info p').textContent = "High confidence weapon signature matched!";
        } else if (status.tamper_active) {
            alertBanner.classList.remove('hidden');
            systemStatusPill.classList.add('alarm');
            statusTextPill.textContent = "TAMPER ALERT";
            document.querySelector('.alert-info h2').textContent = "CAMERA TAMPERED";
            document.querySelector('.alert-info p').textContent = "Camera lens is covered or blocked!";
            alertBanner.style.backgroundColor = "";
            alertBanner.style.borderColor = "";
        } else {
            if (!alertBanner.classList.contains('hidden')) {
                // Alarm cleared server side (e.g. timeout)
                alertBanner.classList.add('hidden');
                systemStatusPill.classList.remove('alarm');
                // Reset styles
                alertBanner.style.backgroundColor = "";
                alertBanner.style.borderColor = "";
            }

            // Text status update
            const isArmed = status.away_mode || status.night_mode_active;
            const isWeaponScan = status.weapon_check_enabled;

            if (isArmed) {
                let txt = "System Armed";
                if (status.night_mode_active) txt = "Night Watch Active";
                if (isWeaponScan) txt += " + Weapon Scan";
                statusTextPill.textContent = txt;
                systemStatusPill.className = "status-pill success active";
            } else if (status.night_mode_enabled && !isArmed) {
                statusTextPill.textContent = "Night Mode Armed";
                systemStatusPill.className = "status-pill";
            } else {
                statusTextPill.textContent = "System Standby";
                systemStatusPill.className = "status-pill";
            }
        }
    }, 1000);
});
