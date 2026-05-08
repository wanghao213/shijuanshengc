/** Axios 客户端实例 */

import axios from 'axios';
import { message } from 'antd';

const client = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 响应拦截器
client.interceptors.response.use(
  (response) => {
    // blob 响应直接返回（文件下载）
    if (response.config.responseType === 'blob') {
      return response;
    }
    const data = response.data;
    // 统一错误处理
    if (data.code && data.code !== 200) {
      message.error(data.message || '请求失败');
      return Promise.reject(new Error(data.message));
    }
    return response;
  },
  (error) => {
    // blob 响应的错误尝试解析为 JSON
    if (error.response?.config?.responseType === 'blob') {
      const reader = new FileReader();
      reader.onload = () => {
        try {
          const errData = JSON.parse(reader.result as string);
          message.error(errData.message || '导出失败');
        } catch {
          message.error('导出失败');
        }
      };
      if (error.response.data instanceof Blob) {
        reader.readAsText(error.response.data);
        return Promise.reject(error);
      }
    }
    const msg = error.response?.data?.message || error.message || '网络错误';
    message.error(msg);
    return Promise.reject(error);
  }
);

export default client;
