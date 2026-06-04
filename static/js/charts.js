let _chartsInitialized = false;

function initCharts(data) {
  if (_chartsInitialized) return;
  _chartsInitialized = true;

  const isDark     = document.documentElement.classList.contains('dark');
  const gridColor  = isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)';
  const labelColor = isDark ? '#94a3b8' : '#64748b';
  const tooltipBg  = isDark ? '#1e293b' : '#ffffff';
  const tooltipClr = isDark ? '#f1f5f9' : '#1e293b';

  const baseTooltip = {
    backgroundColor: tooltipBg,
    titleColor: tooltipClr,
    bodyColor: tooltipClr,
    borderColor: isDark ? '#334155' : '#e2e8f0',
    borderWidth: 1,
    padding: 10,
    cornerRadius: 8,
    displayColors: true,
  };

  // ── 1. ATS Score Breakdown — Horizontal Bar ──────────────────────────────
  const barEl = document.getElementById('barChart');
  if (barEl) {
    const labels = ['Overall', 'ATS', 'Skills', 'Experience', 'Education'];
    const values = [data.overall, data.ats, data.skills, data.experience, data.education];
    const bgColors = values.map(v =>
      v >= 70 ? 'rgba(34,197,94,0.85)' :
      v >= 45 ? 'rgba(245,158,11,0.85)' :
               'rgba(239,68,68,0.85)'
    );

    new Chart(barEl, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label: 'Score',
          data: values,
          backgroundColor: bgColors,
          borderRadius: 6,
          borderSkipped: false,
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        plugins: {
          legend: { display: false },
          tooltip: {
            ...baseTooltip,
            callbacks: { label: ctx => ` ${ctx.raw}%` }
          },
        },
        scales: {
          x: {
            min: 0, max: 100,
            ticks: { color: labelColor, callback: v => v + '%' },
            grid: { color: gridColor },
          },
          y: { ticks: { color: labelColor }, grid: { display: false } },
        },
        animation: { duration: 1000 },
      }
    });
  }

  // ── 2. Skills Match — Pie ────────────────────────────────────────────────
  const pieEl = document.getElementById('pieChart');
  if (pieEl) {
    const found   = data.found   || 0;
    const missing = data.missing || 0;
    const total   = found + missing || 1;

    new Chart(pieEl, {
      type: 'pie',
      data: {
        labels: ['Found', 'Missing'],
        datasets: [{
          data: [found, missing],
          backgroundColor: [
            'rgba(34,197,94,0.85)',
            'rgba(239,68,68,0.85)',
          ],
          borderColor: [
            'rgba(34,197,94,1)',
            'rgba(239,68,68,1)',
          ],
          borderWidth: 2,
          hoverOffset: 6,
        }]
      },
      options: {
        responsive: true,
        plugins: {
          legend: {
            position: 'bottom',
            labels: { color: labelColor, padding: 14, font: { size: 12 } },
          },
          tooltip: {
            ...baseTooltip,
            callbacks: {
              label: ctx => ` ${ctx.label}: ${ctx.raw} (${Math.round(ctx.raw / total * 100)}%)`
            }
          }
        },
        animation: { animateRotate: true, duration: 1000 },
      }
    });
  }

  // ── 3. Section Scores — Radar ────────────────────────────────────────────
  const radarEl = document.getElementById('radarChart');
  if (radarEl && data.sections) {
    new Chart(radarEl, {
      type: 'radar',
      data: {
        labels: ['Skills', 'Experience', 'Education', 'Projects'],
        datasets: [{
          label: 'Score',
          data: [
            data.sections.skills,
            data.sections.experience,
            data.sections.education,
            data.sections.projects,
          ],
          backgroundColor: 'rgba(99,102,241,0.18)',
          borderColor: 'rgba(99,102,241,0.9)',
          borderWidth: 2,
          pointBackgroundColor: 'rgba(99,102,241,1)',
          pointRadius: 4,
          pointHoverRadius: 6,
        }]
      },
      options: {
        responsive: true,
        scales: {
          r: {
            min: 0, max: 100,
            ticks: { stepSize: 25, color: labelColor, backdropColor: 'transparent', font: { size: 10 } },
            grid:        { color: gridColor },
            angleLines:  { color: gridColor },
            pointLabels: { color: labelColor, font: { size: 12 } },
          }
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            ...baseTooltip,
            callbacks: { label: ctx => ` ${ctx.raw}%` }
          }
        },
        animation: { duration: 1000 },
      }
    });
  }

  // ── 4. Overall Match — Doughnut (small, inside the section breakdown card) ─
  const doughnutEl = document.getElementById('doughnutChart');
  if (doughnutEl) {
    const found   = data.found   || 0;
    const missing = data.missing || 0;
    const score   = data.overall || 0;
    const fillColor = score >= 70 ? '#22c55e' : score >= 45 ? '#f59e0b' : '#ef4444';

    new Chart(doughnutEl, {
      type: 'doughnut',
      data: {
        datasets: [{
          data: [found, missing],
          backgroundColor: [fillColor, isDark ? '#1e293b' : '#f1f5f9'],
          borderWidth: 0,
          hoverOffset: 4,
        }]
      },
      options: {
        cutout: '76%',
        responsive: true,
        plugins: {
          legend: { display: false },
          tooltip: {
            ...baseTooltip,
            callbacks: {
              label: ctx => {
                const labels = ['Found', 'Missing'];
                return ` ${labels[ctx.dataIndex]}: ${ctx.raw}`;
              }
            }
          }
        },
        animation: { animateRotate: true, duration: 1200 },
      }
    });
  }
}
