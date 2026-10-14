/**
 * websocket.js - Quản lý Giao thức Mạng WebSocket thời gian thực
 * Phục vụ đồng bộ phòng thi, phát đề, kiểm soát đồng hồ và nhận kết quả
 */

class WebSocketClient {
  constructor() {
    this.lobbyWs = null;
    this.roomWs = null;
    this.currentRoomCode = null;
    this.userName = null;
    this.callbacks = {};
  }

  // Khởi tạo kết nối tới WebSocket Sảnh (Lobby) để nhận danh sách phòng trực tiếp
  connectLobby(onUpdateRooms) {
    if (this.lobbyWs && this.lobbyWs.readyState === WebSocket.OPEN) {
      return;
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/lobby`;

    this.lobbyWs = new WebSocket(wsUrl);

    this.lobbyWs.onopen = () => {
      console.log('[WS LOBBY] Đã kết nối với máy chủ!');
      if (window.updateNetworkStatus) {
        window.updateNetworkStatus(true);
      }
    };

    this.lobbyWs.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'LOBBY_ROOMS_UPDATE' && typeof onUpdateRooms === 'function') {
          onUpdateRooms(data.rooms);
        }
      } catch (err) {
        console.error('[WS LOBBY] Lỗi xử lý thông điệp:', err);
      }
    };

    this.lobbyWs.onerror = (err) => {
      console.error('[WS LOBBY] Lỗi kết nối:', err);
      if (window.updateNetworkStatus) {
        window.updateNetworkStatus(false);
      }
    };

    this.lobbyWs.onclose = () => {
      console.warn('[WS LOBBY] Kết nối bị ngắt, thử kết nối lại sau 3 giây...');
      if (window.updateNetworkStatus) {
        window.updateNetworkStatus(false);
      }
      setTimeout(() => this.connectLobby(onUpdateRooms), 3000);
    };
  }

  // Kết nối vào một phòng thi cụ thể
  connectRoom(roomCode, userName, callbacks = {}) {
    this.disconnectRoom();

    this.currentRoomCode = roomCode;
    this.userName = userName;
    this.callbacks = callbacks;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/room/${encodeURIComponent(roomCode)}/${encodeURIComponent(userName)}`;

    console.log(`[WS ROOM] Đang kết nối tới phòng ${roomCode} với tên ${userName}...`);
    this.roomWs = new WebSocket(wsUrl);

    this.roomWs.onopen = () => {
      console.log(`[WS ROOM] Kết nối thành công tới phòng ${roomCode}`);
      if (callbacks.onConnected) callbacks.onConnected();
    };

    this.roomWs.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        this.handleRoomMessage(msg);
      } catch (err) {
        console.error('[WS ROOM] Lỗi phân tích gói tin:', err);
      }
    };

    this.roomWs.onerror = (err) => {
      console.error('[WS ROOM] Lỗi kết nối phòng:', err);
      if (callbacks.onError) callbacks.onError('Mất kết nối với phòng thi');
    };

    this.roomWs.onclose = () => {
      console.log('[WS ROOM] Đã đóng kết nối phòng thi');
      if (callbacks.onDisconnected) callbacks.onDisconnected();
    };
  }

  // Phân loại và xử lý các sự kiện mạng nhận được từ Server
  handleRoomMessage(msg) {
    console.log('[WS ROOM] Nhận gói tin:', msg.type, msg);

    switch (msg.type) {
      case 'PARTICIPANT_JOINED':
        if (this.callbacks.onParticipantJoined) {
          this.callbacks.onParticipantJoined(msg);
        }
        break;

      case 'EXAM_STARTED':
        if (this.callbacks.onExamStarted) {
          this.callbacks.onExamStarted(msg);
        }
        break;

      case 'EXAM_RECONNECTED':
        if (this.callbacks.onExamReconnected) {
          this.callbacks.onExamReconnected(msg);
        }
        break;

      case 'ANSWER_SAVED':
        if (this.callbacks.onAnswerSaved) {
          this.callbacks.onAnswerSaved(msg);
        }
        break;

      case 'PARTICIPANT_SUBMITTED_NOTIFICATION':
        if (this.callbacks.onPeerSubmitted) {
          this.callbacks.onPeerSubmitted(msg);
        }
        break;

      case 'SUBMISSION_RESULT':
        if (this.callbacks.onPersonalResult) {
          this.callbacks.onPersonalResult(msg);
        }
        break;

      case 'EXAM_FINISHED':
      case 'ROOM_ALREADY_FINISHED':
        if (this.callbacks.onExamFinished) {
          this.callbacks.onExamFinished(msg);
        }
        break;

      case 'ERROR':
        if (this.callbacks.onError) {
          this.callbacks.onError(msg.message);
        }
        break;

      default:
        console.log('Thông điệp chưa định nghĩa handler:', msg);
    }
  }

  // Gửi gói tin JSON lên Server
  send(data) {
    if (this.roomWs && this.roomWs.readyState === WebSocket.OPEN) {
      this.roomWs.send(JSON.stringify(data));
      return true;
    }
    console.warn('[WS ROOM] Không thể gửi vì WebSocket chưa mở');
    return false;
  }

  // Thí sinh thay đổi đáp án câu hỏi
  updateAnswer(questionId, option) {
    return this.send({
      action: 'UPDATE_ANSWER',
      question_id: questionId,
      option: option
    });
  }

  // Thí sinh nộp bài thi
  submitExam(answersMap) {
    return this.send({
      action: 'SUBMIT_EXAM',
      answers: answersMap
    });
  }

  // Chủ phòng bắt đầu kỳ thi
  hostStartExam() {
    return this.send({
      action: 'HOST_START_EXAM'
    });
  }

  // Chủ phòng kết thúc kỳ thi sớm
  hostEndExam() {
    return this.send({
      action: 'HOST_END_EXAM'
    });
  }

  // Ngắt kết nối phòng thi hiện tại
  disconnectRoom() {
    if (this.roomWs) {
      this.roomWs.close();
      this.roomWs = null;
    }
    this.currentRoomCode = null;
  }
}

// Khởi tạo instance toàn cục
const wsClient = new WebSocketClient();
