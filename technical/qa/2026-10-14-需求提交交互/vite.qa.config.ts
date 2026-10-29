import base from '/Users/zhanggengyu/Documents/极简AI团队需求管理智能体/frontend/vite.config.ts'

export default {
  ...base,
  cacheDir: '/private/tmp/requirements-qa-20261014-cPlFUB/vite-cache',
  server: {
    ...base.server,
    host: 'localhost',
    port: 3001,
    proxy: { '/api': { target: 'http://127.0.0.1:8001' } },
  },
}
