/**
 * exam.js - Bộ điều khiển Giao diện Làm bài thi trắc nghiệm (Exam Runner Engine)
 * Phục vụ cả Chế độ Thi Phòng (Multiplayer Room) và Chế độ Luyện Tập (Practice Mode)
 * Cho phép đổi đáp án tự do khi còn thời gian, nộp bài sớm, đồng hồ đếm ngược, bảng điều hướng câu hỏi
 */

class ExamEngine {
  constructor() {
    this.mode = 'practice'; // 'room' hoặc 'practice'
    this.roomCode = null;
    this.roomName = '';
    this.questions = [];
    this.currentIndex = 0;
    this.answers = {}; // { "q_id": "A" }
    this.flagged = new Set();
    this.remainingSeconds = 0;
    this.totalDurationSeconds = 0;
    this.timerInterval = null;
    this.isSubmitted = false;
    this.startTime = null;
  }

  // Khởi động phiên làm bài mới
  initExam({ mode, questions, durationSeconds, roomCode = null, roomName = '', initialAnswers = {} }) {
    this.mode = mode;
    this.questions = questions || [];
    this.totalDurationSeconds = durationSeconds;
    this.remainingSeconds = durationSeconds;
    this.roomCode = roomCode;
    this.roomName = roomName;
    this.currentIndex = 0;
    this.answers = { ...initialAnswers };
    this.flagged.clear();
    this.isSubmitted = false;
    this.startTime = Date.now();

    if (this.timerInterval) {
      clearInterval(this.timerInterval);
    }

    // Hiển thị giao diện làm bài
    document.querySelectorAll('.tab-pane').forEach(el => el.classList.remove('active'));
    const examView = document.getElementById('view-exam');
    if (examView) examView.classList.add('active');

    // Cập nhật thông tin phòng/tiêu đề
    const titleEl = document.getElementById('exam-title-display');
    if (titleEl) {
      titleEl.textContent = mode === 'room' ? `Phòng thi: ${roomName} (${roomCode})` : 'Bài Thi Luyện Tập';
    }

    // Nút dành riêng cho chủ phòng
    const hostEndBtn = document.getElementById('btn-host-end-exam');
    if (hostEndBtn) {
      const isHost = (mode === 'room' && window.appState && window.appState.isCurrentHost);
      hostEndBtn.style.display = isHost ? 'inline-flex' : 'none';
    }

    this.renderPalette();
    this.renderQuestion(0);
    this.startTimer();
    this.updateProgress();
  }

  // Khởi động đồng hồ đếm ngược
  startTimer() {
    this.updateTimerDisplay();
    this.timerInterval = setInterval(() => {
      this.remainingSeconds--;
      this.updateTimerDisplay();

      if (this.remainingSeconds <= 0) {
        clearInterval(this.timerInterval);
        this.timerInterval = null;
        console.log('[EXAM] Hết giờ làm bài! Tự động nộp bài...');
        if (window.showToast) window.showToast('Hết giờ làm bài! Hệ thống đang tự động thu bài...', 'info');
        this.submitExam(false); // Nộp tự động khi hết giờ
      }
    }, 1000);
  }

  // Cập nhật hiển thị thời gian phút:giây
  updateTimerDisplay() {
    const timerBox = document.getElementById('exam-timer-box');
    const timerText = document.getElementById('exam-timer-text');
    if (!timerText) return;

    const mins = Math.floor(Math.max(0, this.remainingSeconds) / 60);
    const secs = Math.max(0, this.remainingSeconds) % 60;
    timerText.textContent = `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;

    if (timerBox) {
      if (this.remainingSeconds <= 60 && this.remainingSeconds > 0) {
        timerBox.classList.add('timer-warning');
      } else {
        timerBox.classList.remove('timer-warning');
      }
    }
  }

  // Hiển thị câu hỏi tại chỉ số index
  renderQuestion(index) {
    if (index < 0 || index >= this.questions.length) return;
    this.currentIndex = index;

    const q = this.questions[index];
    const qIdStr = String(q.id);

    // Cập nhật số thứ tự & huy hiệu độ khó
    const badgeNum = document.getElementById('exam-q-number');
    if (badgeNum) badgeNum.textContent = `Câu ${index + 1} / ${this.questions.length}`;

    const diffBadge = document.getElementById('exam-q-difficulty');
    if (diffBadge) {
      const diffText = q.difficulty === 'easy' ? 'Dễ' : (q.difficulty === 'hard' ? 'Khó' : 'Trung bình');
      diffBadge.className = `diff-badge diff-${q.difficulty || 'medium'}`;
      diffBadge.textContent = diffText;
    }

    const catBadge = document.getElementById('exam-q-category');
    if (catBadge) {
      catBadge.textContent = q.category || 'Mạng máy tính';
    }

    // Nội dung câu hỏi
    const contentEl = document.getElementById('exam-q-content');
    if (contentEl) contentEl.textContent = q.content;

    // Nút Flag
    const flagBtn = document.getElementById('btn-flag-question');
    if (flagBtn) {
      const isFlagged = this.flagged.has(qIdStr);
      flagBtn.innerHTML = isFlagged ? '⭐ Bỏ đánh dấu' : '🚩 Đánh dấu xem lại';
      flagBtn.className = isFlagged ? 'btn btn-sm btn-secondary text-warning' : 'btn btn-sm btn-secondary';
    }

    // Danh sách 4 lựa chọn A, B, C, D
    const optionsContainer = document.getElementById('exam-options-container');
    if (optionsContainer) {
      optionsContainer.innerHTML = '';
      const options = [
        { letter: 'A', text: q.option_a },
        { letter: 'B', text: q.option_b },
        { letter: 'C', text: q.option_c },
        { letter: 'D', text: q.option_d }
      ];

      const currentSelected = this.answers[qIdStr] || '';

      options.forEach(opt => {
        const item = document.createElement('div');
        item.className = `option-item ${currentSelected === opt.letter ? 'selected' : ''}`;
        item.innerHTML = `
          <div class="option-letter-circle">${opt.letter}</div>
          <div class="option-label-text">${opt.text}</div>
        `;

        item.addEventListener('click', () => {
          if (this.isSubmitted) return;
          this.selectAnswer(qIdStr, opt.letter);
        });

        optionsContainer.appendChild(item);
      });
    }

    // Nút Trước / Sau
    const prevBtn = document.getElementById('btn-prev-question');
    const nextBtn = document.getElementById('btn-next-question');
    if (prevBtn) prevBtn.disabled = (index === 0);
    if (nextBtn) nextBtn.disabled = (index === this.questions.length - 1);

    this.updatePaletteCurrent();
  }

  // Thí sinh chọn hoặc thay đổi một đáp án
  selectAnswer(questionIdStr, optionLetter) {
    this.answers[questionIdStr] = optionLetter;

    // Cập nhật giao diện lựa chọn
    const options = document.querySelectorAll('#exam-options-container .option-item');
    options.forEach(item => {
      const letter = item.querySelector('.option-letter-circle').textContent.trim();
      if (letter === optionLetter) {
        item.classList.add('selected');
      } else {
        item.classList.remove('selected');
      }
    });

    // Cập nhật nút số câu trong bảng palette
    const pBtn = document.getElementById(`palette-btn-${this.currentIndex}`);
    if (pBtn) {
      pBtn.classList.add('answered');
    }

    this.updateProgress();

    // Nếu ở chế độ phòng thi mạng, gửi gói tin WebSocket tới Server để lưu trữ thời gian thực
    if (this.mode === 'room' && window.wsClient) {
      window.wsClient.updateAnswer(questionIdStr, optionLetter);
    }
  }

  // Bật/tắt cờ đánh dấu câu hỏi cần xem lại
  toggleFlagCurrent() {
    if (!this.questions[this.currentIndex]) return;
    const qIdStr = String(this.questions[this.currentIndex].id);
    if (this.flagged.has(qIdStr)) {
      this.flagged.delete(qIdStr);
    } else {
      this.flagged.add(qIdStr);
    }
    this.renderQuestion(this.currentIndex);
    this.renderPalette();
  }

  // Xây dựng bảng điều hướng câu hỏi (Question Matrix / Palette)
  renderPalette() {
    const paletteGrid = document.getElementById('exam-palette-grid');
    if (!paletteGrid) return;
    paletteGrid.innerHTML = '';

    this.questions.forEach((q, idx) => {
      const btn = document.createElement('button');
      btn.id = `palette-btn-${idx}`;
      btn.className = 'palette-btn';
      btn.textContent = idx + 1;

      const qIdStr = String(q.id);
      if (this.answers[qIdStr]) btn.classList.add('answered');
      if (this.flagged.has(qIdStr)) btn.classList.add('flagged');
      if (idx === this.currentIndex) btn.classList.add('current');

      btn.addEventListener('click', () => {
        this.renderQuestion(idx);
      });

      paletteGrid.appendChild(btn);
    });
  }

  // Đổi trạng thái ô đang xem trên bảng Palette
  updatePaletteCurrent() {
    document.querySelectorAll('.palette-btn').forEach((btn, idx) => {
      if (idx === this.currentIndex) {
        btn.classList.add('current');
      } else {
        btn.classList.remove('current');
      }
    });
  }

  // Cập nhật thanh tiến độ làm bài
  updateProgress() {
    const answeredCount = Object.keys(this.answers).length;
    const total = this.questions.length;
    const pct = total > 0 ? (answeredCount / total) * 100 : 0;

    const fillEl = document.getElementById('exam-progress-fill');
    const textEl = document.getElementById('exam-progress-text');
    if (fillEl) fillEl.style.width = `${pct}%`;
    if (textEl) textEl.textContent = `Đã làm ${answeredCount}/${total} câu`;
  }

  // Chuyển sang câu hỏi kế tiếp
  nextQuestion() {
    if (this.currentIndex < this.questions.length - 1) {
      this.renderQuestion(this.currentIndex + 1);
    }
  }

  // Chuyển về câu hỏi trước
  prevQuestion() {
    if (this.currentIndex > 0) {
      this.renderQuestion(this.currentIndex - 1);
    }
  }

  // Nộp bài thi (Người dùng chủ động nộp sớm hoặc hết giờ)
  async submitExam(isManual = true) {
    if (this.isSubmitted) return;

    const answeredCount = Object.keys(this.answers).length;
    const total = this.questions.length;

    if (isManual) {
      const unAns = total - answeredCount;
      let confirmMsg = `Bạn có chắc chắn muốn nộp bài sớm không?\n- Đã làm: ${answeredCount}/${total} câu.`;
      if (unAns > 0) {
        confirmMsg += `\n⚠️ Chú ý: Còn ${unAns} câu bạn chưa trả lời!`;
      }
      if (!confirm(confirmMsg)) {
        return;
      }
    }

    this.isSubmitted = true;
    if (this.timerInterval) {
      clearInterval(this.timerInterval);
      this.timerInterval = null;
    }

    const durationSeconds = Math.max(1, Math.round((Date.now() - this.startTime) / 1000));

    if (this.mode === 'room') {
      // Chế độ phòng thi mạng: Gửi kết quả qua WebSocket
      if (window.wsClient) {
        window.wsClient.submitExam(this.answers);
      }
      if (window.showToast) {
        window.showToast('Đã nộp bài thành công! Đang chờ kết quả từ Server...', 'success');
      }
    } else {
      // Chế độ luyện tập: Gửi REST API và nhận kết quả chi tiết tức thì
      try {
        const payload = {
          user_name: window.appState ? window.appState.userName : 'Học Viên',
          question_ids: this.questions.map(q => q.id),
          answers: this.answers,
          duration_seconds: durationSeconds
        };

        const result = await API.submitPractice(payload);
        if (result.success) {
          this.showPracticeResultModal(result);
        }
      } catch (err) {
        alert('Lỗi nộp bài luyện tập: ' + err.message);
      }
    }
  }

  // Hiển thị modal kết quả tức thì cho chế độ Luyện tập
  showPracticeResultModal(result) {
    const modal = document.getElementById('modal-practice-result');
    if (!modal) return;

    document.getElementById('pr-score-display').textContent = result.score.toFixed(1);
    document.getElementById('pr-correct-display').textContent = `${result.correct_count}/${result.total_questions}`;
    document.getElementById('pr-pct-display').textContent = `${result.percentage}%`;

    // Nhận xét
    let evalText = 'Cần nỗ lực hơn nữa!';
    if (result.score >= 8.5) evalText = '🌟 Xuất sắc!';
    else if (result.score >= 7.0) evalText = '👍 Rất tốt!';
    else if (result.score >= 5.0) evalText = 'Đạt yêu cầu.';
    document.getElementById('pr-evaluation-text').textContent = evalText;

    // Lưu danh sách chi tiết để người dùng xem lại
    this.lastResultDetails = result.details;

    modal.classList.add('active');
  }
}

// Khởi tạo instance toàn cục
const examEngine = new ExamEngine();
