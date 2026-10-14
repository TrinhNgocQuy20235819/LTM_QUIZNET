/**
 * charts.js - Quản lý và Vẽ Đồ Thị Thống Kê Điểm Số & Năng Lực (Chart.js)
 * Cung cấp:
 * 1. Biểu đồ biến động điểm số qua các bài thi (Score Trend Line Chart)
 * 2. Biểu đồ độ chính xác theo độ khó Dễ - Trung Bình - Khó (Bar Chart)
 * 3. Biểu đồ tỷ lệ câu đúng / câu sai (Doughnut Chart)
 * Tự động thích ứng màu sắc theo Giao diện Sáng (Light Mode) hoặc Tối (Dark Mode)
 */

class AnalyticsCharts {
  constructor() {
    this.scoreTrendChart = null;
    this.difficultyChart = null;
    this.ratioChart = null;
  }

  // Khởi tạo hoặc cập nhật tất cả đồ thị từ dữ liệu thống kê
  renderCharts(analyticsData) {
    if (!analyticsData || !window.Chart) return;

    this.renderScoreTrend(analyticsData.score_trend || []);
    this.renderDifficultyStats(analyticsData.difficulty_stats || {});
    this.renderResultsRatio(analyticsData.results_distribution || { correct: 0, wrong: 0 });
  }

  // Lấy màu sắc phù hợp với Theme hiện tại
  getThemeColors() {
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    return {
      isDark,
      gridColor: isDark ? 'rgba(255, 255, 255, 0.08)' : 'rgba(15, 23, 42, 0.08)',
      tickColor: isDark ? '#94a3b8' : '#475569',
      tooltipBg: isDark ? 'rgba(17, 24, 39, 0.95)' : 'rgba(15, 23, 42, 0.95)',
      titleColor: '#ffffff',
      bodyColor: isDark ? '#a5b4fc' : '#cbd5e1'
    };
  }

  // 1. Biểu đồ biến động điểm số theo thời gian (Line Chart)
  renderScoreTrend(trendData) {
    const ctx = document.getElementById('chart-score-trend');
    if (!ctx) return;

    if (this.scoreTrendChart) {
      this.scoreTrendChart.destroy();
    }

    const { gridColor, tickColor, tooltipBg, titleColor, bodyColor } = this.getThemeColors();

    const labels = trendData.map((item, idx) => {
      const date = new Date(item.date);
      return `${date.getDate()}/${date.getMonth() + 1} #${idx + 1}`;
    });

    const scores = trendData.map(item => item.score);

    // Tạo gradient màu nền cho đường biểu diễn
    const canvas = ctx.getContext('2d');
    const gradient = canvas.createLinearGradient(0, 0, 0, 260);
    gradient.addColorStop(0, 'rgba(79, 70, 229, 0.35)');
    gradient.addColorStop(1, 'rgba(79, 70, 229, 0.0)');

    this.scoreTrendChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels.length ? labels : ['Chưa có bài thi'],
        datasets: [{
          label: 'Điểm số (Thang 10)',
          data: scores.length ? scores : [0],
          borderColor: '#4f46e5',
          borderWidth: 3,
          backgroundColor: gradient,
          fill: true,
          tension: 0.35,
          pointBackgroundColor: '#fff',
          pointBorderColor: '#4f46e5',
          pointBorderWidth: 2,
          pointRadius: 5,
          pointHoverRadius: 7
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: tooltipBg,
            titleColor: titleColor,
            bodyColor: bodyColor,
            borderColor: 'rgba(255,255,255,0.1)',
            borderWidth: 1,
            padding: 10,
            callbacks: {
              afterLabel: function(context) {
                const item = trendData[context.dataIndex];
                if (item) {
                  return `Bài: ${item.title}\nĐúng: ${item.correct_count}/${item.total_questions} câu`;
                }
                return '';
              }
            }
          }
        },
        scales: {
          y: {
            min: 0,
            max: 10,
            grid: { color: gridColor },
            ticks: { color: tickColor, font: { family: 'Plus Jakarta Sans', weight: '500' } }
          },
          x: {
            grid: { display: false },
            ticks: { color: tickColor, font: { family: 'Plus Jakarta Sans', weight: '500' } }
          }
        }
      }
    });
  }

  // 2. Biểu đồ tỷ lệ làm đúng theo độ khó Dễ - Trung bình - Khó (Bar Chart)
  renderDifficultyStats(diffStats) {
    const ctx = document.getElementById('chart-difficulty-stats');
    if (!ctx) return;

    if (this.difficultyChart) {
      this.difficultyChart.destroy();
    }

    const { gridColor, tickColor } = this.getThemeColors();

    const easyPct = diffStats.easy && diffStats.easy.total > 0 
      ? Math.round((diffStats.easy.correct / diffStats.easy.total) * 100) : 0;
    const medPct = diffStats.medium && diffStats.medium.total > 0 
      ? Math.round((diffStats.medium.correct / diffStats.medium.total) * 100) : 0;
    const hardPct = diffStats.hard && diffStats.hard.total > 0 
      ? Math.round((diffStats.hard.correct / diffStats.hard.total) * 100) : 0;

    this.difficultyChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: ['Dễ', 'Trung Bình', 'Khó'],
        datasets: [{
          label: 'Tỷ lệ đúng (%)',
          data: [easyPct, medPct, hardPct],
          backgroundColor: [
            'rgba(16, 185, 129, 0.85)',
            'rgba(245, 158, 11, 0.85)',
            'rgba(239, 68, 68, 0.85)'
          ],
          borderRadius: 6,
          barThickness: 34
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function(context) {
                return `Độ chính xác: ${context.parsed.y}%`;
              }
            }
          }
        },
        scales: {
          y: {
            min: 0,
            max: 100,
            grid: { color: gridColor },
            ticks: {
              color: tickColor,
              font: { family: 'Plus Jakarta Sans', weight: '500' },
              callback: value => `${value}%`
            }
          },
          x: {
            grid: { display: false },
            ticks: { color: tickColor, font: { family: 'Plus Jakarta Sans', weight: '600' } }
          }
        }
      }
    });
  }

  // 3. Biểu đồ phân bố Đúng vs Sai (Doughnut Chart)
  renderResultsRatio(distData) {
    const ctx = document.getElementById('chart-results-ratio');
    if (!ctx) return;

    if (this.ratioChart) {
      this.ratioChart.destroy();
    }

    const { tickColor } = this.getThemeColors();

    const correct = distData.correct || 0;
    const wrong = distData.wrong || 0;
    const hasData = (correct + wrong) > 0;

    this.ratioChart = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: ['Trả lời đúng', 'Trả lời sai / Bỏ qua'],
        datasets: [{
          data: hasData ? [correct, wrong] : [1, 0],
          backgroundColor: hasData 
            ? ['rgba(16, 185, 129, 0.85)', 'rgba(239, 68, 68, 0.85)']
            : ['rgba(15, 23, 42, 0.1)', 'rgba(15, 23, 42, 0.05)'],
          borderWidth: 0,
          hoverOffset: 4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              color: tickColor,
              font: { family: 'Plus Jakarta Sans', size: 12, weight: '600' },
              padding: 16
            }
          }
        },
        cutout: '72%'
      }
    });
  }
}

// Khởi tạo instance toàn cục
const analyticsCharts = new AnalyticsCharts();
