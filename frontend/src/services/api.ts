import axios from 'axios';

const API_BASE = 'http://localhost:8000/api/v1';

export const plmApi = {
  getItems: (skip = 0, limit = 100) =>
    axios.get(`${API_BASE}/items/`, { params: { skip, limit } }).then(res => res.data),

  getBOM: (revId: string, type: string = "EBOM") =>
    axios.get(`${API_BASE}/bom/${revId}`, { params: { bom_type: type } }).then(res => res.data),

  uploadFile: (revId: string, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return axios.post(`${API_BASE}/vault/upload/${revId}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    }).then(res => res.data);
  },

  processFEA: (fileId: string) =>
    axios.post(`${API_BASE}/fea/process/${fileId}`).then(res => res.data),

  promoteRevision: (revId: string) =>
    axios.post(`${API_BASE}/workflow/promote/${revId}`).then(res => res.data),
};
