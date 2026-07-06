import api from './api';

export const searchService = {
  async search(query, { limit = 20 } = {}) {
    const trimmed = (query || '').trim();
    if (trimmed.length < 2) {
      return { query: trimmed, results: [], total: 0 };
    }
    const { data } = await api.get('/search/', {
      params: { q: trimmed, limit },
    });
    return data?.data ?? data;
  },
};

export default searchService;