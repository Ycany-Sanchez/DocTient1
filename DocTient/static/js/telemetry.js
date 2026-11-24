/* DocTient — Interactive Biometric Telemetry Charts, Danger Thresholds & Zero-Refresh Controls */
(() => {
  const METRIC_CONFIG = {
    bp: {
      title: 'Blood pressure trajectory',
      unit: 'mmHg',
      rangeText: 'Safe <120/80 · Elevated 120–129 · Danger ≥140/90 mmHg',
      build(data) {
        return {
          series: [
            { name: 'Systolic', values: data.systolic },
            { name: 'Diastolic', values: data.diastolic },
          ],
          min: 60,
          format: (v) => `${Math.round(v)} mmHg`,
          tickFormat: (v) => `${Math.round(v)}`,
          reference: [
            { value: 140, label: 'Danger 140' },
            { value: 120, label: 'Optimal 120', at: 'left' },
          ],
          dangerAbove: 140,
        };
      },
    },
    hr: {
      title: 'Heart rate trend',
      unit: 'bpm',
      rangeText: 'Safe 60–100 · Danger <55 or >105 bpm',
      build(data) {
        return {
          series: [{ name: 'Heart rate', values: data.heartRate }],
          min: 40,
          format: (v) => `${Math.round(v)} bpm`,
          tickFormat: (v) => `${Math.round(v)}`,
          reference: [
            { value: 105, label: 'High danger 105' },
            { value: 55, label: 'Low danger 55', at: 'left' },
          ],
          dangerAbove: 105,
          dangerBelow: 55,
        };
      },
    },
    spo2: {
      title: 'Oxygen saturation (SpO₂)',
      unit: '%',
      rangeText: 'Safe 95–100% · Low 92–94% · Danger <92%',
      build(data) {
        return {
          series: [{ name: 'SpO₂', values: data.spo2 }],
          min: 88,
          max: 100,
          yTicks: [88, 92, 96, 100],
          format: (v) => `${Number(v).toFixed(1)}%`,
          tickFormat: (v) => `${Math.round(v)}%`,
          reference: [{ value: 92, label: 'Danger <92%' }],
          dangerBelow: 92,
        };
      },
    },
    temp: {
      title: 'Body temperature',
      unit: '°C',
      rangeText: 'Safe 35.5–37.4°C · Elevated 37.5–37.9°C · Fever ≥38.0°C',
      build(data) {
        return {
          series: [{ name: 'Temperature', values: data.temperature }],
          min: 35.0,
          max: 39.5,
          yTicks: [35, 36, 37, 38, 39],
          format: (v) => `${Number(v).toFixed(1)}°C`,
          tickFormat: (v) => `${Number(v).toFixed(1)}°`,
          reference: [
            { value: 38.0, label: 'Fever 38.0°C' },
            { value: 35.5, label: 'Low 35.5°C', at: 'left' },
          ],
          dangerAbove: 38.0,
          dangerBelow: 35.5,
        };
      },
    },
    weight: {
      title: 'Body weight log',
      unit: 'kg',
      rangeText: 'Longitudinal body weight tracking across sessions',
      build(data) {
        const vals = data.weight.filter((v) => v != null);
        const lo = vals.length ? Math.max(30, Math.floor(Math.min(...vals) - 4)) : 40;
        const hi = vals.length ? Math.ceil(Math.max(...vals) + 4) : 100;
        return {
          series: [{ name: 'Weight', values: data.weight }],
          min: lo,
          max: hi,
          format: (v) => `${Number(v).toFixed(1)} kg`,
          tickFormat: (v) => `${Number(v).toFixed(0)}`,
          reference: null,
        };
      },
    },
  };

  function initSidebar() {
    const toggle = document.getElementById('menuToggle');
    const closeBtn = document.getElementById('sidebarClose');
    const sidebar = document.getElementById('appSidebar');
    const backdrop = document.getElementById('sidebarBackdrop');
    if (!sidebar) return;

    const setOpen = (open) => {
      sidebar.classList.toggle('is-open', open);
      if (backdrop) backdrop.classList.toggle('is-open', open);
      if (toggle) toggle.setAttribute('aria-expanded', String(open));
      document.body.style.overflow = open ? 'hidden' : '';
    };

    toggle?.addEventListener('click', () => setOpen(!sidebar.classList.contains('is-open')));
    closeBtn?.addEventListener('click', () => setOpen(false));
    backdrop?.addEventListener('click', () => setOpen(false));
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && sidebar.classList.contains('is-open')) setOpen(false);
    });
  }

  function renderClinicalChart(container, data, key, titleEl, subEl, legendEl) {
    if (!container || !window.Charts || !data || !Array.isArray(data.labels) || !data.labels.length) {
      return;
    }
    const cfg = METRIC_CONFIG[key] || METRIC_CONFIG.bp;
    const built = cfg.build(data);
    const hasValues = built.series.some((s) => s.values.some((v) => v != null));

    if (titleEl) titleEl.textContent = cfg.title;
    if (subEl) subEl.textContent = cfg.rangeText;

    if (!hasValues) {
      container.innerHTML = `<div class="empty">No ${cfg.title.toLowerCase()} measurements recorded yet.</div>`;
      if (legendEl) legendEl.innerHTML = '';
      return;
    }

    // Highlight points that breach clinical danger thresholds using chart annotations
    const annotations = [];
    const primary = built.series[0].values;
    primary.forEach((v, i) => {
      if (v == null) return;
      if (built.dangerAbove != null && v >= built.dangerAbove) {
        annotations.push({
          at: i,
          label: `${built.format(v)} danger`,
          short: built.format(v),
          colour: getComputedStyle(document.documentElement).getPropertyValue('--negative').trim() || '#be1e2d',
        });
      } else if (built.dangerBelow != null && v < built.dangerBelow) {
        annotations.push({
          at: i,
          label: `${built.format(v)} low`,
          short: built.format(v),
          colour: getComputedStyle(document.documentElement).getPropertyValue('--negative').trim() || '#be1e2d',
        });
      }
    });

    const result = window.Charts.line(container, {
      labels: data.labels,
      series: built.series,
      format: built.format,
      tickFormat: built.tickFormat,
      height: 264,
      fill: built.series.length === 1,
      min: built.min,
      max: built.max,
      yTicks: built.yTicks || null,
      reference: built.reference,
      annotations: annotations.slice(-3),
      legend: legendEl || null,
    });

    // Tint clinical danger / optimal reference labels cleanly for instant legibility
    const rootStyle = getComputedStyle(document.documentElement);
    const negCol = rootStyle.getPropertyValue('--negative').trim() || '#be1e2d';
    const posCol = rootStyle.getPropertyValue('--positive').trim() || '#156e44';
    container.querySelectorAll('svg text').forEach((t) => {
      const txt = (t.textContent || '').trim();
      if (/^(Danger|High danger|Low danger|Fever|Low )/i.test(txt)) {
        t.setAttribute('fill', negCol);
        t.setAttribute('font-weight', '500');
      } else if (/^Optimal/i.test(txt)) {
        t.setAttribute('fill', posCol);
        t.setAttribute('font-weight', '500');
      }
    });

    if (legendEl && (!result || !result.legend)) {
      legendEl.innerHTML = '';
    }
  }

  function initTelemetryDecks() {
    document.querySelectorAll('[data-telemetry-deck]').forEach((deck) => {
      const scriptId = deck.getAttribute('data-chart-source');
      const dataEl = scriptId ? document.getElementById(scriptId) : null;
      if (!dataEl) return;

      let data;
      try {
        data = JSON.parse(dataEl.textContent);
      } catch {
        return;
      }

      const chartEl = deck.querySelector('[data-chart-target]');
      const titleEl = deck.querySelector('[data-chart-title]');
      const subEl = deck.querySelector('[data-chart-sub]');
      const legendEl = deck.querySelector('[data-chart-legend]');
      const tabs = [...deck.querySelectorAll('[role="tab"][data-vital-key]')];

      let activeKey = deck.getAttribute('data-initial-metric') || 'bp';

      const selectMetric = (key) => {
        activeKey = key;
        tabs.forEach((t) => {
          const isMatch = t.getAttribute('data-vital-key') === key;
          t.setAttribute('aria-selected', String(isMatch));
          t.tabIndex = isMatch ? 0 : -1;
        });
        renderClinicalChart(chartEl, data, key, titleEl, subEl, legendEl);
      };

      tabs.forEach((tab) => {
        tab.addEventListener('click', () => selectMetric(tab.getAttribute('data-vital-key')));
        tab.addEventListener('keydown', (e) => {
          const idx = tabs.indexOf(tab);
          if (e.key === 'ArrowRight') {
            e.preventDefault();
            const next = tabs[(idx + 1) % tabs.length];
            next.focus();
            selectMetric(next.getAttribute('data-vital-key'));
          } else if (e.key === 'ArrowLeft') {
            e.preventDefault();
            const prev = tabs[(idx - 1 + tabs.length) % tabs.length];
            prev.focus();
            selectMetric(prev.getAttribute('data-vital-key'));
          }
        });
      });

      selectMetric(activeKey);
    });
  }

  function showToast(msg, isError = false) {
    let region = document.getElementById('liveToast');
    if (!region) {
      region = document.createElement('div');
      region.id = 'liveToast';
      region.className = 'live-toast';
      region.setAttribute('role', 'status');
      region.setAttribute('aria-live', 'polite');
      document.body.appendChild(region);
    }
    region.textContent = msg;
    region.classList.toggle('is-error', isError);
    region.classList.add('is-visible');
    clearTimeout(region._timer);
    region._timer = setTimeout(() => region.classList.remove('is-visible'), 2800);
  }

  function initAjaxMedications() {
    // Patient: Mark taken / Undo without page reload
    document.querySelectorAll('.js-med-toggle-form').forEach((form) => {
      form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = form.querySelector('button[type="submit"]');
        const row = form.closest('[data-med-row]');
        if (!btn || btn.disabled) return;

        btn.disabled = true;
        btn.setAttribute('aria-busy', 'true');
        const originalText = btn.textContent;

        try {
          const body = new FormData(form);
          body.set('action', 'toggle_medication_taken');

          const res = await fetch(form.getAttribute('action') || window.location.href, {
            method: 'POST',
            headers: {
              'X-Requested-With': 'XMLHttpRequest',
              Accept: 'application/json',
            },
            body,
            credentials: 'same-origin',
          });

          if (!res.ok) throw new Error('Request failed');
          const data = await res.json();
          if (!data.ok) throw new Error(data.error || 'Update failed');

          // Update row state immediately
          if (row) {
            row.classList.toggle('is-taken', data.taken_today);
            const pill = row.querySelector('[data-med-pill]');
            if (pill) {
              pill.className = data.taken_today ? 'pill pos' : 'pill warn';
              pill.textContent = data.taken_today ? 'Taken today' : 'Due today';
            }
          }

          btn.className = data.taken_today ? 'btn btn-sm js-med-btn is-taken' : 'btn btn-sm primary js-med-btn';
          btn.innerHTML = data.taken_today
            ? '<svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3.5 8.5 6.5 11.5 12.5 4.5"/></svg> Taken'
            : 'Mark taken';
          btn.setAttribute('aria-pressed', String(data.taken_today));

          // Reconcile adherence summary & top finding line live
          const countEl = document.getElementById('medTakenCount');
          const pctEl = document.getElementById('medAdherencePct');
          const barEl = document.getElementById('medAdherenceFill');
          const findingMeds = document.getElementById('findingMedsText');

          if (countEl) countEl.textContent = `${data.taken_today_count} of ${data.total_active_meds} taken`;
          if (pctEl) pctEl.textContent = `${data.today_adherence_pct}%`;
          if (barEl) {
            barEl.style.width = `${data.today_adherence_pct}%`;
            barEl.setAttribute('aria-valuenow', String(data.today_adherence_pct));
          }
          if (findingMeds) {
            findingMeds.textContent = data.due_count === 0
              ? `All ${data.total_active_meds} prescriptions taken today`
              : `${data.due_count} of ${data.total_active_meds} prescriptions due today`;
          }

          showToast(
            data.taken_today
              ? `${data.medication_name} marked as taken.`
              : `${data.medication_name} unmarked for today.`
          );
        } catch {
          btn.textContent = originalText;
          showToast('Could not save medication status. Try again.', true);
        } finally {
          btn.disabled = false;
          btn.removeAttribute('aria-busy');
        }
      });
    });

    // Doctor: Discontinue / Reactivate prescription without page reload
    document.querySelectorAll('.js-doc-med-toggle-form').forEach((form) => {
      form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = form.querySelector('button[type="submit"]');
        const row = form.closest('[data-doc-med-row]');
        if (!btn || btn.disabled) return;

        btn.disabled = true;
        try {
          const res = await fetch(form.getAttribute('action') || window.location.href, {
            method: 'POST',
            headers: {
              'X-Requested-With': 'XMLHttpRequest',
              Accept: 'application/json',
            },
            body: new FormData(form),
            credentials: 'same-origin',
          });
          if (!res.ok) throw new Error('Request failed');
          const data = await res.json();
          if (!data.ok) throw new Error(data.error || 'Update failed');

          const isActive = data.status === 'active';
          if (row) {
            const pill = row.querySelector('[data-doc-med-pill]');
            if (pill) {
              pill.className = isActive ? 'pill pos' : 'pill';
              pill.textContent = data.status_label;
            }
          }
          btn.textContent = isActive ? 'Discontinue' : 'Reactivate';
          btn.className = isActive ? 'btn btn-sm' : 'btn btn-sm primary';
          showToast(`Prescription set to ${data.status_label}.`);
        } catch {
          showToast('Could not update prescription status.', true);
        } finally {
          btn.disabled = false;
        }
      });
    });
  }

  function initVitalLivePreview() {
    const form = document.querySelector('[data-vital-form]');
    const preview = document.getElementById('vitalRiskPreview');
    if (!form || !preview) return;

    const readNum = (name) => {
      const el = form.querySelector(`[name="${name}"]`);
      const v = el ? parseFloat(el.value) : NaN;
      return Number.isFinite(v) ? v : null;
    };

    const update = () => {
      const sys = readNum('systolic');
      const dia = readNum('diastolic');
      const hr = readNum('heart_rate');
      const spo2 = readNum('oxygen_saturation');
      const temp = readNum('temperature_celsius');

      if (sys == null && dia == null && hr == null && spo2 == null && temp == null) {
        preview.className = 'pill';
        preview.textContent = 'Auto-evaluated on entry';
        return;
      }

      if ((sys != null && sys >= 140) || (dia != null && dia >= 90)) {
        preview.className = 'pill neg';
        preview.textContent = 'Danger · Stage 2 HTN';
      } else if (spo2 != null && spo2 < 92) {
        preview.className = 'pill neg';
        preview.textContent = 'Danger · Low SpO₂';
      } else if (temp != null && (temp >= 38.0 || temp < 35.5)) {
        preview.className = 'pill neg';
        preview.textContent = temp >= 38.0 ? 'Danger · Fever' : 'Danger · Hypothermia';
      } else if (hr != null && (hr < 55 || hr > 105)) {
        preview.className = 'pill neg';
        preview.textContent = 'Danger · Abnormal HR';
      } else if ((sys != null && sys >= 130) || (dia != null && dia >= 80)) {
        preview.className = 'pill warn';
        preview.textContent = 'Caution · Stage 1 HTN';
      } else if (sys != null && sys >= 120) {
        preview.className = 'pill warn';
        preview.textContent = 'Elevated BP';
      } else {
        preview.className = 'pill pos';
        preview.textContent = 'Within normal range';
      }
    };

    form.addEventListener('input', update);
  }

  function initDarkModePreview() {
    const toggle = document.getElementById('dark_mode');
    if (!toggle) return;
    toggle.addEventListener('change', () => {
      if (toggle.checked) {
        document.documentElement.setAttribute('data-theme', 'dark');
      } else {
        document.documentElement.removeAttribute('data-theme');
      }
    });
  }

  function initRolePicker() {
    const radios = document.querySelectorAll('input[name="role"]');
    const spec = document.getElementById('specialtyGroup');
    if (!radios.length || !spec) return;
    const sync = () => {
      const checked = document.querySelector('input[name="role"]:checked');
      spec.style.display = checked && checked.value === 'doctor' ? 'block' : 'none';
    };
    radios.forEach((r) => r.addEventListener('change', sync));
    sync();
  }

  function initVitalDrawer() {
    const openBtn = document.getElementById('openVitalDrawerBtn');
    const drawer = document.getElementById('logReadingDrawer');
    const backdrop = document.getElementById('vitalDrawerBackdrop');
    const closeBtn = document.getElementById('closeVitalDrawerBtn');
    const cancelBtn = document.getElementById('cancelVitalDrawerBtn');
    if (!openBtn || !drawer) return;

    const setOpen = (open) => {
      drawer.hidden = !open;
      if (backdrop) backdrop.hidden = !open;
      openBtn.setAttribute('aria-expanded', String(open));
      document.body.style.overflow = open ? 'hidden' : '';
      if (open) {
        const firstInput = drawer.querySelector('#in_systolic');
        firstInput?.focus();
      } else {
        openBtn.focus();
      }
    };

    openBtn.addEventListener('click', () => setOpen(true));
    closeBtn?.addEventListener('click', () => setOpen(false));
    cancelBtn?.addEventListener('click', () => setOpen(false));
    backdrop?.addEventListener('click', () => setOpen(false));
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && !drawer.hidden) setOpen(false);
    });
  }

  function initReportAnalytics() {
    if (!window.Charts) return;
    document.querySelectorAll('[data-bullet-chart]').forEach((el) => {
      const srcId = el.getAttribute('data-bullet-chart');
      const dataEl = srcId ? document.getElementById(srcId) : null;
      if (!dataEl) return;
      let rows;
      try {
        rows = JSON.parse(dataEl.textContent);
      } catch {
        return;
      }
      if (!Array.isArray(rows) || !rows.length) {
        el.innerHTML = '<div class="empty">No compliance records logged yet.</div>';
        return;
      }
      window.Charts.bullet(el, rows, {
        format: window.Charts.fmt.pct(0),
        max: 1.0,
        higherIsBetter: true,
      });
    });
  }

  function initDynamicBars() {
    document.querySelectorAll('[data-width], [data-left], [data-right]').forEach((el) => {
      const w = el.getAttribute('data-width');
      const l = el.getAttribute('data-left');
      const r = el.getAttribute('data-right');
      if (w) el.style.width = w;
      if (l) el.style.left = l;
      if (r) el.style.right = r;
    });
  }

  // Hydrate bar geometry immediately before first paint (script loads at end of <body>)
  initDynamicBars();

  document.addEventListener('DOMContentLoaded', () => {
    initDynamicBars();
    initSidebar();
    initTelemetryDecks();
    initReportAnalytics();
    initAjaxMedications();
    initVitalLivePreview();
    initVitalDrawer();
    initDarkModePreview();
    initRolePicker();
  });
})();
