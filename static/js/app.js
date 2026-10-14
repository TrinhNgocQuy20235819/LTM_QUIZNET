/**
 * app.js - Trình điều phối Trung tâm Giao diện Ứng dụng (Single Page Application)
 * Xử lý: Chuyển đổi tab, Quản lý người dùng, Tương tác phòng thi, Modal và Toast
 */

// Trạng thái toàn cục ứng dụng
window.appState = {
  userName: localStorage.getItem('quiz_user_name') || 'Thí sinh ' + Math.floor(100 + Math.random() * 900),
  activeTab: 'rooms',
  currentRoom: null,
  isCurrentHost: false,
  allRooms: []
};

// Cập nhật trạng thái biểu tượng kết nối mạng
window.updateNetworkStatus = function(isOnline) {
  const badge = document.getElementById('network-status-badge');
  if (!badge) return;
  if (isOnline) {
    badge.className = 'network-badge';
    badge.innerHTML = '<span class="pulse-dot"></span><span>Trực tuyến</span>';
  } else {
    badge.className = 'network-badge disconnected';
    badge.innerHTML = '<span class="pulse-dot"></span><span>Mất kết nối</span>';
  }
};

// Hiển thị thông báo Toast góc màn hình
window.showToast = function(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
};

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  initUserProfile();
  initNavigation();
  initModals();
  initPracticeTab();
  initQuestionBankTab();

  // Kết nối WebSocket Sảnh và tải danh sách phòng ban đầu
  wsClient.connectLobby((rooms) => {
    window.appState.allRooms = rooms;
    renderRoomsList(rooms);
  });

  // Tải danh sách phòng qua REST lần đầu
  loadRoomsREST();
});

// ==========================================
// QUẢN LÝ GIAO DIỆN SÁNG / TỐI (THEME)
// ==========================================
function initTheme() {
  const savedTheme = localStorage.getItem('quiz_theme') || 'light';
  applyTheme(savedTheme);

  const toggleBtn = document.getElementById('btn-toggle-theme');
  if (toggleBtn) {
    toggleBtn.addEventListener('click', () => {
      const current = document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
      const next = (current === 'light') ? 'dark' : 'light';
      applyTheme(next);
      localStorage.setItem('quiz_theme', next);
      window.showToast(`Đã chuyển sang ${next === 'light' ? 'Giao diện Sáng ☀️' : 'Giao diện Tối 🌙'}`, 'info');
      // Nếu đang ở tab thống kê thì cập nhật lại biểu đồ cho phù hợp màu nền
      if (window.appState && window.appState.activeTab === 'history') {
        loadHistoryAndAnalytics();
      }
    });
  }
}

function applyTheme(theme) {
  const iconEl = document.getElementById('theme-toggle-icon');
  const textEl = document.getElementById('theme-toggle-text');

  if (theme === 'dark') {
    document.documentElement.setAttribute('data-theme', 'dark');
    if (iconEl) iconEl.textContent = '☀️';
    if (textEl) textEl.textContent = 'Sáng';
  } else {
    document.documentElement.removeAttribute('data-theme');
    if (iconEl) iconEl.textContent = '🌙';
    if (textEl) textEl.textContent = 'Tối';
  }
}

// ==========================================
// QUẢN LÝ NGƯỜI DÙNG & TÊN HIỂN THỊ
// ==========================================
function initUserProfile() {
  const nameEl = document.getElementById('header-user-name');
  const avatarEl = document.getElementById('header-user-avatar');
  if (nameEl) nameEl.textContent = window.appState.userName;
  if (avatarEl) avatarEl.textContent = window.appState.userName.charAt(0).toUpperCase();

  const userBadge = document.getElementById('btn-change-user-name');
  if (userBadge) {
    userBadge.addEventListener('click', () => {
      const newName = prompt('Nhập họ tên hoặc biệt danh của bạn:', window.appState.userName);
      if (newName && newName.trim().length >= 2) {
        window.appState.userName = newName.trim();
        localStorage.setItem('quiz_user_name', window.appState.userName);
        if (nameEl) nameEl.textContent = window.appState.userName;
        if (avatarEl) avatarEl.textContent = window.appState.userName.charAt(0).toUpperCase();
        window.showToast(`Đã đổi tên thành: ${window.appState.userName}`, 'success');
      }
    });
  }
}

// ==========================================
// ĐIỀU HƯỚNG TAB
// ==========================================
function initNavigation() {
  const tabBtns = document.querySelectorAll('.nav-tab-btn');
  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const tabId = btn.getAttribute('data-tab');
      switchTab(tabId);
    });
  });
}

function switchTab(tabId) {
  window.appState.activeTab = tabId;

  // Đổi trạng thái nút bấm
  document.querySelectorAll('.nav-tab-btn').forEach(btn => {
    if (btn.getAttribute('data-tab') === tabId) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });

  // Hiển thị khung nội dung tương ứng
  document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('active'));
  const targetPane = document.getElementById(`tab-${tabId}`);
  if (targetPane) targetPane.classList.add('active');

  // Nạp dữ liệu tương ứng của tab đó
  if (tabId === 'rooms') {
    loadRoomsREST();
  } else if (tabId === 'bank') {
    loadQuestionsBank();
  } else if (tabId === 'history') {
    loadHistoryAndAnalytics();
  }
}

// ==========================================
// TAB 1: PHÒNG THI TRỰC TUYẾN
// ==========================================
async function loadRoomsREST() {
  const res = await API.getRooms();
  window.appState.allRooms = res.rooms || [];
  renderRoomsList(window.appState.allRooms);
}

function renderRoomsList(rooms) {
  const container = document.getElementById('rooms-grid-container');
  if (!container) return;

  const currentFilter = document.querySelector('.filter-pill-btn.active')?.getAttribute('data-filter') || 'all';
  const searchTerm = (document.getElementById('input-search-room')?.value || '').toLowerCase().trim();

  let filtered = rooms.filter(r => {
    if (currentFilter !== 'all' && r.status !== currentFilter) return false;
    if (searchTerm) {
      const matchName = r.room_name.toLowerCase().includes(searchTerm);
      const matchCode = r.room_code.toLowerCase().includes(searchTerm);
      const matchHost = r.host_name.toLowerCase().includes(searchTerm);
      return matchName || matchCode || matchHost;
    }
    return true;
  });

  if (filtered.length === 0) {
    container.innerHTML = `
      <div style="grid-column: 1/-1; text-align: center; padding: 3rem 1rem; color: var(--text-muted);">
        <p style="font-size: 1.1rem; margin-bottom: 0.5rem;">Không tìm thấy phòng thi nào phù hợp</p>
        <p style="font-size: 0.85rem;">Hãy tạo một phòng thi mới hoặc đổi bộ lọc tìm kiếm!</p>
      </div>
    `;
    return;
  }

  container.innerHTML = filtered.map(room => {
    let statusPill = '';
    let actionBtn = '';

    if (room.status === 'waiting') {
      statusPill = `<span class="status-pill status-waiting">🟡 Chưa bắt đầu</span>`;
      actionBtn = `<button class="btn btn-primary" onclick="joinRoom('${room.room_code}')">🚀 Tham gia phòng</button>`;
    } else if (room.status === 'in_progress') {
      statusPill = `<span class="status-pill status-in_progress">🟢 Đang diễn ra</span>`;
      actionBtn = `<button class="btn btn-secondary" onclick="joinRoom('${room.room_code}')">⚡ Vào phòng thi</button>`;
    } else {
      statusPill = `<span class="status-pill status-finished">🔴 Đã kết thúc</span>`;
      actionBtn = `<button class="btn btn-secondary" onclick="viewFinishedRoomResults('${room.room_code}')">🏆 Xem kết quả & Bảng xếp hạng</button>`;
    }

    return `
      <div class="room-card">
        <div>
          <div class="room-card-header">
            <div>
              <h3 class="room-card-title">${escapeHtml(room.room_name)}</h3>
              <div style="font-size: 0.8rem; color: var(--text-muted); margin-top: 0.2rem;">Chủ phòng: <strong style="color: #fff;">${escapeHtml(room.host_name)}</strong></div>
            </div>
            <div class="room-code-badge" onclick="copyRoomCode('${room.room_code}')" title="Bấm để sao chép mã">
              <span>#${room.room_code}</span> 📋
            </div>
          </div>

          <div style="margin-bottom: 0.75rem;">
            ${statusPill}
          </div>

          <div class="room-meta-grid">
            <div class="meta-item">
              <span class="meta-label">Thời gian thi</span>
              <span class="meta-value">⏱️ ${room.duration_minutes} phút</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">Số câu hỏi</span>
              <span class="meta-value">📝 ${room.num_questions} câu</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">Thí sinh</span>
              <span class="meta-value">👥 ${room.participant_count} người</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">Phân loại</span>
              <span class="meta-value">
                <span style="color:#34d399">${room.easy_count}D</span> / 
                <span style="color:#fbbf24">${room.medium_count}TB</span> / 
                <span style="color:#f87171">${room.hard_count}K</span>
              </span>
            </div>
          </div>
        </div>

        <div class="room-card-actions">
          ${actionBtn}
        </div>
      </div>
    `;
  }).join('');
}

// Bộ lọc trạng thái phòng
document.querySelectorAll('.filter-pill-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.filter-pill-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    renderRoomsList(window.appState.allRooms);
  });
});

// Tìm kiếm phòng
const searchInput = document.getElementById('input-search-room');
if (searchInput) {
  searchInput.addEventListener('input', () => {
    renderRoomsList(window.appState.allRooms);
  });
}

function copyRoomCode(code) {
  navigator.clipboard.writeText(code).then(() => {
    window.showToast(`Đã sao chép mã phòng: ${code}`, 'success');
  });
}

// Tham gia vào một phòng thi
window.joinRoom = function(roomCode) {
  const userName = window.appState.userName;
  console.log(`Tham gia phòng ${roomCode} với tên ${userName}...`);

  // Hiển thị màn hình phòng chờ
  document.querySelectorAll('.tab-pane').forEach(el => el.classList.remove('active'));
  const lobbyView = document.getElementById('view-room-lobby');
  if (lobbyView) lobbyView.classList.add('active');

  // Đăng ký các callback xử lý sự kiện qua WebSocket
  wsClient.connectRoom(roomCode, userName, {
    onConnected: () => {
      window.showToast(`Đã vào phòng thi ${roomCode}`, 'success');
    },

    onParticipantJoined: (msg) => {
      renderLobbyWaitingRoom(roomCode, msg.participants);
    },

    onExamStarted: (msg) => {
      window.showToast('🚀 Bài thi đã chính thức bắt đầu! Chúc bạn làm bài tốt!', 'success');
      examEngine.initExam({
        mode: 'room',
        questions: msg.questions,
        durationSeconds: msg.duration_seconds,
        roomCode: msg.room_code,
        roomName: msg.room_name
      });
    },

    onExamReconnected: (msg) => {
      window.showToast('Đã kết nối lại bài thi đang diễn ra', 'info');
      examEngine.initExam({
        mode: 'room',
        questions: msg.questions,
        durationSeconds: msg.remaining_seconds,
        roomCode: roomCode,
        roomName: `Phòng ${roomCode}`,
        initialAnswers: msg.saved_answers || {}
      });
      if (msg.is_submitted) {
        examEngine.isSubmitted = true;
        window.showToast('Bạn đã nộp bài trước đó, đang chờ phòng thi kết thúc.', 'info');
      }
    },

    onPeerSubmitted: (msg) => {
      window.showToast(`🔔 Thí sinh ${msg.user_name} đã nộp bài (${msg.submitted_count}/${msg.total_count})`, 'info');
    },

    onPersonalResult: (msg) => {
      window.showToast(`Bạn trả lời đúng ${msg.correct_count}/${msg.total_questions} câu! (Điểm: ${msg.score})`, 'success');
      // Lưu lại thông tin chi tiết bài thi để xem lại
      examEngine.lastResultDetails = msg.details;
    },

    onExamFinished: (msg) => {
      renderExamFinishedScreen(msg.room_code, msg.leaderboard, msg.personal_result);
    },

    onError: (errMsg) => {
      alert(errMsg);
      switchTab('rooms');
    }
  });
};

// Hiển thị thông tin phòng chờ
function renderLobbyWaitingRoom(roomCode, participants) {
  document.getElementById('lobby-room-code').textContent = roomCode;
  const currentRoom = window.appState.allRooms.find(r => r.room_code === roomCode);
  const roomName = currentRoom ? currentRoom.room_name : `Phòng ${roomCode}`;
  document.getElementById('lobby-room-name').textContent = roomName;

  const isHost = participants.some(p => p.user_name === window.appState.userName && p.is_host);
  window.appState.isCurrentHost = isHost;

  const hostActions = document.getElementById('lobby-host-actions');
  const memberWaiting = document.getElementById('lobby-member-waiting');
  if (isHost) {
    if (hostActions) hostActions.style.display = 'block';
    if (memberWaiting) memberWaiting.style.display = 'none';
  } else {
    if (hostActions) hostActions.style.display = 'none';
    if (memberWaiting) memberWaiting.style.display = 'block';
  }

  // Danh sách thí sinh trong phòng
  const grid = document.getElementById('lobby-participants-grid');
  const countEl = document.getElementById('lobby-participant-count');
  if (countEl) countEl.textContent = `${participants.length} người`;

  if (grid) {
    grid.innerHTML = participants.map(p => `
      <div class="participant-card ${p.is_host ? 'is-host' : ''}">
        <div class="user-avatar-circle" style="width:30px;height:30px;font-size:0.8rem;">
          ${p.user_name.charAt(0).toUpperCase()}
        </div>
        <div style="font-size:0.9rem; font-weight:600; color:#fff;">
          ${escapeHtml(p.user_name)}
        </div>
        ${p.is_host ? '<span class="host-badge-tag">Chủ phòng</span>' : ''}
      </div>
    `).join('');
  }
}

// Chủ phòng bấm Bắt đầu thi
document.getElementById('btn-host-start-exam')?.addEventListener('click', () => {
  wsClient.hostStartExam();
});

// Chủ phòng kết thúc thi sớm
document.getElementById('btn-host-end-exam')?.addEventListener('click', () => {
  if (confirm('Bạn có chắc chắn muốn KẾT THÚC phòng thi ngay bây giờ? Tất cả bài làm sẽ được tự động thu và chấm điểm.')) {
    wsClient.hostEndExam();
  }
});

// Rời phòng chờ
document.getElementById('btn-leave-lobby')?.addEventListener('click', () => {
  wsClient.disconnectRoom();
  switchTab('rooms');
});

// Hiển thị màn hình kết quả thi & Bảng xếp hạng khi phòng kết thúc
function renderExamFinishedScreen(roomCode, leaderboard, personalResult = null) {
  document.querySelectorAll('.tab-pane').forEach(el => el.classList.remove('active'));
  const resView = document.getElementById('view-room-results');
  if (resView) resView.classList.add('active');

  document.getElementById('res-room-code').textContent = roomCode;

  // Podium Top 3
  const top1 = leaderboard[0] || null;
  const top2 = leaderboard[1] || null;
  const top3 = leaderboard[2] || null;

  renderPodiumUser('podium-top1', top1);
  renderPodiumUser('podium-top2', top2);
  renderPodiumUser('podium-top3', top3);

  // Bảng xếp hạng chi tiết
  const tableBody = document.getElementById('leaderboard-table-body');
  if (tableBody) {
    tableBody.innerHTML = leaderboard.map(item => {
      let rankBadge = `<span class="rank-badge">${item.rank}</span>`;
      if (item.rank === 1) rankBadge = `<span class="rank-badge rank-1">🥇</span>`;
      else if (item.rank === 2) rankBadge = `<span class="rank-badge rank-2">🥈</span>`;
      else if (item.rank === 3) rankBadge = `<span class="rank-badge rank-3">🥉</span>`;

      const isMe = (item.user_name === window.appState.userName);

      return `
        <tr style="${isMe ? 'background: rgba(99,102,241,0.15);' : ''}">
          <td>${rankBadge}</td>
          <td>
            <strong style="color: ${isMe ? '#a5b4fc' : '#fff'};">
              ${escapeHtml(item.user_name)} ${isMe ? '(Bạn)' : ''}
            </strong>
          </td>
          <td><strong style="color: #34d399; font-size: 1.05rem;">${item.score.toFixed(1)}</strong></td>
          <td>${item.correct_count} / ${item.total_questions}</td>
          <td>${item.time_taken_seconds}s</td>
          <td>
            <span style="color: ${item.is_submitted ? '#34d399' : '#f87171'}">
              ${item.is_submitted ? 'Đã nộp bài' : 'Hết giờ tự nộp'}
            </span>
          </td>
        </tr>
      `;
    }).join('');
  }

  // Nút xem chi tiết bài làm cá nhân
  const viewDetailBtn = document.getElementById('btn-view-personal-details');
  if (viewDetailBtn) {
    if (personalResult && personalResult.details && personalResult.details.length > 0) {
      viewDetailBtn.style.display = 'inline-flex';
      viewDetailBtn.onclick = () => {
        showExamDetailsModal('Kết quả bài thi phòng ' + roomCode, personalResult.details);
      };
    } else {
      viewDetailBtn.style.display = 'none';
    }
  }
}

function renderPodiumUser(elementId, userData) {
  const container = document.getElementById(elementId);
  if (!container) return;
  if (!userData) {
    container.innerHTML = `<span style="color:var(--text-dim); font-size:0.8rem;">Trống</span>`;
    return;
  }
  container.innerHTML = `
    <div style="font-weight:700; color:#fff; font-size:0.95rem;">${escapeHtml(userData.user_name)}</div>
    <div style="font-size:0.82rem; color:#34d399; font-weight:700;">${userData.score.toFixed(1)} điểm</div>
    <div style="font-size:0.75rem; color:var(--text-muted);">${userData.correct_count}/${userData.total_questions} câu</div>
  `;
}

// Xem kết quả của phòng thi đã kết thúc từ danh sách phòng
window.viewFinishedRoomResults = async function(roomCode) {
  try {
    const res = await API.getRoomResults(roomCode);
    renderExamFinishedScreen(roomCode, res.leaderboard, null);
  } catch (err) {
    alert(err.message);
  }
};

// ==========================================
// TAB 2: CHẾ ĐỘ LUYỆN TẬP
// ==========================================
function initPracticeTab() {
  // Nạp danh mục chủ đề
  API.getCategories().then(res => {
    const selectEl = document.getElementById('practice-category-select');
    if (selectEl && res.categories) {
      selectEl.innerHTML = '<option value="all">Tất cả chủ đề</option>' + 
        res.categories.map(c => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join('');
    }
  });

  const startBtn = document.getElementById('btn-start-practice');
  if (startBtn) {
    startBtn.addEventListener('click', async () => {
      const duration = parseInt(document.getElementById('practice-duration').value) || 10;
      const easy = parseInt(document.getElementById('practice-easy').value) || 0;
      const medium = parseInt(document.getElementById('practice-medium').value) || 0;
      const hard = parseInt(document.getElementById('practice-hard').value) || 0;
      const category = document.getElementById('practice-category-select')?.value || 'all';

      const total = easy + medium + hard;
      if (total <= 0) {
        alert('Vui lòng chọn ít nhất 1 câu hỏi!');
        return;
      }

      startBtn.disabled = true;
      startBtn.textContent = 'Đang tải đề thi...';

      try {
        const res = await API.startPractice({
          user_name: window.appState.userName,
          duration_minutes: duration,
          easy_count: easy,
          medium_count: medium,
          hard_count: hard,
          category: category
        });

        if (res.success && res.questions.length > 0) {
          examEngine.initExam({
            mode: 'practice',
            questions: res.questions,
            durationSeconds: res.duration_seconds
          });
        }
      } catch (err) {
        alert('Lỗi tạo bài luyện tập: ' + err.message);
      } finally {
        startBtn.disabled = false;
        startBtn.textContent = '🚀 Bắt đầu luyện tập ngay';
      }
    });
  }

  // Xem chi tiết đáp án bài luyện tập vừa hoàn thành
  document.getElementById('btn-view-practice-details')?.addEventListener('click', () => {
    document.getElementById('modal-practice-result')?.classList.remove('active');
    if (examEngine.lastResultDetails) {
      showExamDetailsModal('Chi tiết bài thi luyện tập', examEngine.lastResultDetails);
    }
  });
}

// ==========================================
// TAB 3: NGÂN HÀNG CÂU HỎI
// ==========================================
function initQuestionBankTab() {
  document.getElementById('filter-bank-diff')?.addEventListener('change', loadQuestionsBank);
  document.getElementById('input-bank-search')?.addEventListener('input', debounce(loadQuestionsBank, 300));

  // Tải danh mục vào bộ lọc
  API.getCategories().then(res => {
    const filterCat = document.getElementById('filter-bank-cat');
    const modalCat = document.getElementById('new-q-category');
    if (res.categories) {
      const opts = res.categories.map(c => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join('');
      if (filterCat) filterCat.innerHTML = '<option value="all">Tất cả chủ đề</option>' + opts;
      if (modalCat) modalCat.innerHTML = opts;
    }
  });
}

async function loadQuestionsBank() {
  const diff = document.getElementById('filter-bank-diff')?.value || 'all';
  const cat = document.getElementById('filter-bank-cat')?.value || 'all';
  const search = document.getElementById('input-bank-search')?.value || '';

  const res = await API.getQuestions(diff, cat, search);
  renderQuestionsBank(res.questions || []);
}

function renderQuestionsBank(questions) {
  const listContainer = document.getElementById('question-bank-list');
  const countEl = document.getElementById('bank-total-count');
  if (countEl) countEl.textContent = `${questions.length} câu hỏi`;
  if (!listContainer) return;

  if (questions.length === 0) {
    listContainer.innerHTML = `<div style="text-align:center; padding:3rem; color:var(--text-muted);">Không tìm thấy câu hỏi nào.</div>`;
    return;
  }

  listContainer.innerHTML = questions.map((q, idx) => {
    const diffBadge = `<span class="diff-badge diff-${q.difficulty}">` + 
      (q.difficulty === 'easy' ? 'Dễ' : (q.difficulty === 'hard' ? 'Khó' : 'Trung bình')) + `</span>`;

    return `
      <div class="question-card-main" style="margin-bottom:1.5rem; padding:1.5rem;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.75rem;">
          <div style="display:flex; align-items:center; gap:0.5rem;">
            <span class="question-badge-num">#${idx + 1}</span>
            ${diffBadge}
            <span style="font-size:0.8rem; color:var(--text-dim);">${escapeHtml(q.category)}</span>
          </div>
          <span style="font-size:0.8rem; color:var(--text-muted); font-family:var(--font-mono);">ID: ${q.id}</span>
        </div>

        <div style="font-size:1.05rem; font-weight:600; color:#fff; margin-bottom:1rem;">
          ${escapeHtml(q.content)}
        </div>

        <div style="display:grid; grid-template-columns:1fr 1fr; gap:0.6rem; margin-bottom:1rem;">
          <div class="option-item ${q.correct_answer === 'A' ? 'selected' : ''}" style="padding:0.65rem 1rem;">
            <div class="option-letter-circle" style="width:26px; height:26px; font-size:0.8rem;">A</div>
            <div class="option-label-text" style="font-size:0.9rem;">${escapeHtml(q.option_a)}</div>
          </div>
          <div class="option-item ${q.correct_answer === 'B' ? 'selected' : ''}" style="padding:0.65rem 1rem;">
            <div class="option-letter-circle" style="width:26px; height:26px; font-size:0.8rem;">B</div>
            <div class="option-label-text" style="font-size:0.9rem;">${escapeHtml(q.option_b)}</div>
          </div>
          <div class="option-item ${q.correct_answer === 'C' ? 'selected' : ''}" style="padding:0.65rem 1rem;">
            <div class="option-letter-circle" style="width:26px; height:26px; font-size:0.8rem;">C</div>
            <div class="option-label-text" style="font-size:0.9rem;">${escapeHtml(q.option_c)}</div>
          </div>
          <div class="option-item ${q.correct_answer === 'D' ? 'selected' : ''}" style="padding:0.65rem 1rem;">
            <div class="option-letter-circle" style="width:26px; height:26px; font-size:0.8rem;">D</div>
            <div class="option-label-text" style="font-size:0.9rem;">${escapeHtml(q.option_d)}</div>
          </div>
        </div>

        ${q.explanation ? `
          <div style="background:rgba(0,0,0,0.25); border-left:3px solid var(--primary); padding:0.65rem 1rem; border-radius:0 var(--radius-sm) var(--radius-sm) 0; font-size:0.85rem; color:var(--text-muted);">
            💡 <strong>Giải thích:</strong> ${escapeHtml(q.explanation)}
          </div>
        ` : ''}
      </div>
    `;
  }).join('');
}

// ==========================================
// TAB 4: LỊCH SỬ & THỐNG KÊ BIỂU ĐỒ
// ==========================================
async function loadHistoryAndAnalytics() {
  const userName = window.appState.userName;

  // 1. Tải và vẽ biểu đồ thống kê
  const analytics = await API.getUserAnalytics(userName);
  if (analytics) {
    document.getElementById('kpi-total-exams').textContent = analytics.total_exams;
    document.getElementById('kpi-avg-score').textContent = analytics.avg_score.toFixed(1);
    document.getElementById('kpi-highest-score').textContent = analytics.highest_score.toFixed(1);
    document.getElementById('kpi-accuracy-pct').textContent = `${analytics.overall_accuracy}%`;

    analyticsCharts.renderCharts(analytics);
  }

  // 2. Tải bảng danh sách lịch sử bài thi đã làm
  const histRes = await API.getUserHistory(userName);
  const tbody = document.getElementById('history-table-body');
  if (!tbody) return;

  const list = histRes.history || [];
  if (list.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding:2.5rem; color:var(--text-muted);">Chưa có bài thi nào được ghi nhận. Hãy tham gia phòng thi hoặc làm bài luyện tập!</td></tr>`;
    return;
  }

  tbody.innerHTML = list.map(item => {
    const isRoom = (item.exam_type === 'room');
    const badgeType = isRoom 
      ? `<span class="diff-badge diff-medium">🏢 Phòng thi</span>` 
      : `<span class="diff-badge diff-easy">⚡ Luyện tập</span>`;

    const dateStr = new Date(item.completed_at).toLocaleString('vi-VN');

    return `
      <tr>
        <td>${badgeType}</td>
        <td><strong>${escapeHtml(item.title)}</strong></td>
        <td><strong style="color:#34d399; font-size:1.05rem;">${item.score.toFixed(1)}</strong></td>
        <td>${item.correct_count} / ${item.total_questions}</td>
        <td>${Math.floor(item.duration_seconds / 60)}p ${item.duration_seconds % 60}s</td>
        <td style="font-size:0.85rem; color:var(--text-dim);">${dateStr}</td>
        <td>
          <button class="btn btn-sm btn-secondary" onclick="viewHistoryDetail(${item.id})">
            🔍 Xem lại bài
          </button>
        </td>
      </tr>
    `;
  }).join('');
}

window.viewHistoryDetail = async function(historyId) {
  try {
    const res = await API.getHistoryDetail(historyId);
    if (res && res.details && res.details.questions) {
      showExamDetailsModal(res.title, res.details.questions);
    }
  } catch (err) {
    alert(err.message);
  }
};

// Modal xem lại chi tiết bài làm (Đúng / Sai / Lời giải)
function showExamDetailsModal(title, questions) {
  const modal = document.getElementById('modal-review-exam');
  if (!modal) return;

  document.getElementById('review-exam-title').textContent = title;
  const container = document.getElementById('review-questions-container');

  if (container) {
    container.innerHTML = questions.map((q, idx) => {
      const isCorrect = q.is_correct;
      const userAns = q.user_answer || 'Chưa trả lời';
      const correctAns = q.correct_answer;

      return `
        <div style="background:rgba(0,0,0,0.3); border:1px solid ${isCorrect ? 'rgba(16,185,129,0.3)' : 'rgba(239,68,68,0.3)'}; border-radius:var(--radius-md); padding:1.25rem; margin-bottom:1rem;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.75rem;">
            <div style="display:flex; align-items:center; gap:0.5rem;">
              <span class="question-badge-num">Câu ${idx + 1}</span>
              <span class="status-pill ${isCorrect ? 'status-in_progress' : 'status-waiting'}">
                ${isCorrect ? '✅ Trả lời đúng' : '❌ Trả lời sai'}
              </span>
            </div>
            <span style="font-size:0.85rem; color:var(--text-dim);">${q.category || ''}</span>
          </div>

          <div style="font-weight:600; color:#fff; margin-bottom:1rem;">
            ${escapeHtml(q.content)}
          </div>

          <div style="display:grid; grid-template-columns:1fr 1fr; gap:0.5rem; margin-bottom:0.75rem; font-size:0.88rem;">
            <div style="padding:0.5rem 0.75rem; border-radius:var(--radius-sm); background:${correctAns === 'A' ? 'rgba(16,185,129,0.2)' : 'rgba(255,255,255,0.03)'}; border:1px solid ${correctAns === 'A' ? 'var(--success)' : 'transparent'};">
              <strong>A.</strong> ${escapeHtml(q.option_a)} ${userAns === 'A' ? '👈 (Bạn chọn)' : ''}
            </div>
            <div style="padding:0.5rem 0.75rem; border-radius:var(--radius-sm); background:${correctAns === 'B' ? 'rgba(16,185,129,0.2)' : 'rgba(255,255,255,0.03)'}; border:1px solid ${correctAns === 'B' ? 'var(--success)' : 'transparent'};">
              <strong>B.</strong> ${escapeHtml(q.option_b)} ${userAns === 'B' ? '👈 (Bạn chọn)' : ''}
            </div>
            <div style="padding:0.5rem 0.75rem; border-radius:var(--radius-sm); background:${correctAns === 'C' ? 'rgba(16,185,129,0.2)' : 'rgba(255,255,255,0.03)'}; border:1px solid ${correctAns === 'C' ? 'var(--success)' : 'transparent'};">
              <strong>C.</strong> ${escapeHtml(q.option_c)} ${userAns === 'C' ? '👈 (Bạn chọn)' : ''}
            </div>
            <div style="padding:0.5rem 0.75rem; border-radius:var(--radius-sm); background:${correctAns === 'D' ? 'rgba(16,185,129,0.2)' : 'rgba(255,255,255,0.03)'}; border:1px solid ${correctAns === 'D' ? 'var(--success)' : 'transparent'};">
              <strong>D.</strong> ${escapeHtml(q.option_d)} ${userAns === 'D' ? '👈 (Bạn chọn)' : ''}
            </div>
          </div>

          ${q.explanation ? `
            <div style="background:rgba(99,102,241,0.08); border-left:3px solid var(--primary); padding:0.5rem 0.75rem; font-size:0.82rem; color:var(--text-muted); border-radius:0 var(--radius-sm) var(--radius-sm) 0;">
              💡 <strong>Lời giải:</strong> ${escapeHtml(q.explanation)}
            </div>
          ` : ''}
        </div>
      `;
    }).join('');
  }

  modal.classList.add('active');
}

// ==========================================
// QUẢN LÝ CÁC MODAL
// ==========================================
function initModals() {
  // Đóng modal khi bấm nút close hoặc click ra ngoài backdrop
  document.querySelectorAll('.modal-close-btn, .btn-close-modal').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.modal-backdrop').forEach(m => m.classList.remove('active'));
    });
  });

  document.querySelectorAll('.modal-backdrop').forEach(modal => {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) modal.classList.remove('active');
    });
  });

  // Mở modal tạo phòng thi
  document.getElementById('btn-open-create-room')?.addEventListener('click', () => {
    document.getElementById('modal-create-room')?.classList.add('active');
  });

  // Xử lý submit tạo phòng thi mới
  document.getElementById('form-create-room')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const name = document.getElementById('cr-room-name').value.trim();
    const duration = parseInt(document.getElementById('cr-duration').value) || 15;
    const easy = parseInt(document.getElementById('cr-easy').value) || 0;
    const medium = parseInt(document.getElementById('cr-medium').value) || 0;
    const hard = parseInt(document.getElementById('cr-hard').value) || 0;

    if (easy + medium + hard <= 0) {
      alert('Vui lòng thiết lập ít nhất 1 câu hỏi!');
      return;
    }

    try {
      const res = await API.createRoom({
        room_name: name,
        host_name: window.appState.userName,
        duration_minutes: duration,
        easy_count: easy,
        medium_count: medium,
        hard_count: hard
      });

      document.getElementById('modal-create-room')?.classList.remove('active');
      window.showToast(`Đã tạo phòng thi: ${res.room_code}`, 'success');

      // Tự động đưa chủ phòng vào phòng chờ
      joinRoom(res.room_code);
    } catch (err) {
      alert('Lỗi tạo phòng: ' + err.message);
    }
  });

  // Mở modal nhập mã phòng để tham gia
  document.getElementById('btn-open-join-code')?.addEventListener('click', () => {
    const code = prompt('Nhập mã phòng thi (6 ký tự, ví dụ: RM1024):');
    if (code && code.trim().length >= 3) {
      joinRoom(code.trim().toUpperCase());
    }
  });

  // Mở modal thêm câu hỏi mới vào ngân hàng
  document.getElementById('btn-open-add-question')?.addEventListener('click', () => {
    document.getElementById('modal-add-question')?.classList.add('active');
  });

  // Xử lý submit thêm câu hỏi
  document.getElementById('form-add-question')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const data = {
      content: document.getElementById('new-q-content').value.trim(),
      option_a: document.getElementById('new-q-opt-a').value.trim(),
      option_b: document.getElementById('new-q-opt-b').value.trim(),
      option_c: document.getElementById('new-q-opt-c').value.trim(),
      option_d: document.getElementById('new-q-opt-d').value.trim(),
      correct_answer: document.getElementById('new-q-correct').value,
      difficulty: document.getElementById('new-q-diff').value,
      category: document.getElementById('new-q-category').value,
      explanation: document.getElementById('new-q-explain').value.trim()
    };

    try {
      await API.addQuestion(data);
      document.getElementById('modal-add-question')?.classList.remove('active');
      window.showToast('Đã thêm câu hỏi vào ngân hàng!', 'success');
      loadQuestionsBank();
    } catch (err) {
      alert('Lỗi thêm câu hỏi: ' + err.message);
    }
  });

  // Các nút bấm trên màn hình thi
  document.getElementById('btn-prev-question')?.addEventListener('click', () => examEngine.prevQuestion());
  document.getElementById('btn-next-question')?.addEventListener('click', () => examEngine.nextQuestion());
  document.getElementById('btn-flag-question')?.addEventListener('click', () => examEngine.toggleFlagCurrent());
  document.getElementById('btn-submit-exam')?.addEventListener('click', () => examEngine.submitExam(true));

  // Quay về trang phòng từ màn hình kết quả
  document.getElementById('btn-back-to-rooms')?.addEventListener('click', () => {
    wsClient.disconnectRoom();
    switchTab('rooms');
  });
}

// Hàm bổ trợ debounce
function debounce(func, wait) {
  let timeout;
  return function(...args) {
    clearTimeout(timeout);
    timeout = setTimeout(() => func.apply(this, args), wait);
  };
}

// Hàm escape HTML chống XSS
function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
