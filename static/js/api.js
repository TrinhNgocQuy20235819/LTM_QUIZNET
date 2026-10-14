/**
 * api.js - Tầng giao tiếp HTTP REST API với Backend FastAPI
 * Quản lý các hàm gọi dữ liệu phòng thi, câu hỏi, luyện tập, lịch sử và thống kê
 */

const API = {
  // Lấy danh sách các chủ đề câu hỏi
  async getCategories() {
    try {
      const res = await fetch('/api/categories');
      return await res.json();
    } catch (err) {
      console.error('Lỗi khi tải danh mục chủ đề:', err);
      return { categories: [] };
    }
  },

  // Truy vấn danh sách câu hỏi trong ngân hàng
  async getQuestions(difficulty = 'all', category = 'all', search = '') {
    try {
      let url = `/api/questions?difficulty=${encodeURIComponent(difficulty)}&category=${encodeURIComponent(category)}`;
      if (search) {
        url += `&search=${encodeURIComponent(search)}`;
      }
      const res = await fetch(url);
      return await res.json();
    } catch (err) {
      console.error('Lỗi khi tải câu hỏi:', err);
      return { total: 0, questions: [] };
    }
  },

  // Thêm một câu hỏi mới vào CSDL
  async addQuestion(questionData) {
    const res = await fetch('/api/questions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(questionData)
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Không thể thêm câu hỏi');
    }
    return await res.json();
  },

  // Lấy danh sách toàn bộ phòng thi
  async getRooms() {
    try {
      const res = await fetch('/api/rooms');
      return await res.json();
    } catch (err) {
      console.error('Lỗi khi tải danh sách phòng thi:', err);
      return { rooms: [] };
    }
  },

  // Tạo một phòng thi mới
  async createRoom(roomData) {
    const res = await fetch('/api/rooms', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(roomData)
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Không thể tạo phòng thi');
    }
    return await res.json();
  },

  // Lấy thông tin chi tiết của phòng thi
  async getRoomDetail(roomCode) {
    const res = await fetch(`/api/rooms/${roomCode}`);
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Không thể lấy thông tin phòng');
    }
    return await res.json();
  },

  // Xem kết quả & Bảng xếp hạng của phòng thi đã kết thúc
  async getRoomResults(roomCode) {
    const res = await fetch(`/api/rooms/${roomCode}/results`);
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Không thể lấy kết quả phòng thi');
    }
    return await res.json();
  },

  // Khởi động bài thi luyện tập cá nhân
  async startPractice(practiceConfig) {
    const res = await fetch('/api/practice/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(practiceConfig)
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Không thể bắt đầu bài luyện tập');
    }
    return await res.json();
  },

  // Nộp bài thi luyện tập cá nhân
  async submitPractice(submissionData) {
    const res = await fetch('/api/practice/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(submissionData)
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Lỗi khi nộp bài thi luyện tập');
    }
    return await res.json();
  },

  // Lấy lịch sử làm bài của người dùng
  async getUserHistory(userName) {
    try {
      const res = await fetch(`/api/history/${encodeURIComponent(userName)}`);
      return await res.json();
    } catch (err) {
      console.error('Lỗi khi lấy lịch sử làm bài:', err);
      return { history: [] };
    }
  },

  // Lấy chi tiết câu hỏi & đáp án của một bài thi trong lịch sử
  async getHistoryDetail(historyId) {
    const res = await fetch(`/api/history/detail/${historyId}`);
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Không thể xem chi tiết bài thi');
    }
    return await res.json();
  },

  // Lấy dữ liệu thống kê biểu đồ của người dùng
  async getUserAnalytics(userName) {
    try {
      const res = await fetch(`/api/analytics/${encodeURIComponent(userName)}`);
      return await res.json();
    } catch (err) {
      console.error('Lỗi khi lấy thống kê:', err);
      return null;
    }
  }
};
