import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { getDataStats, http, searchStocks } from '@/api/index'

describe('api/index 封装', () => {
  beforeEach(() => {
    // 拦截器里会 console.error，测试时静音
    vi.spyOn(console, 'error').mockImplementation(() => {})
  })

  afterEach(() => {
    vi.restoreAllMocks()
    delete http.defaults.adapter
  })

  describe('响应错误拦截器', () => {
    it('优先取后端 detail 作为错误消息', async () => {
      http.defaults.adapter = () =>
        Promise.reject({ response: { data: { detail: '分组不存在' } } })

      await expect(getDataStats()).rejects.toThrow('分组不存在')
    })

    it('无 detail 时回退到 err.message', async () => {
      http.defaults.adapter = () => Promise.reject({ message: 'Network Error' })

      await expect(getDataStats()).rejects.toThrow('Network Error')
    })

    it('既无 detail 也无 message 时回退到默认文案', async () => {
      http.defaults.adapter = () => Promise.reject({})

      await expect(getDataStats()).rejects.toThrow('请求失败')
    })

    it('拒绝值始终是 Error 实例', async () => {
      http.defaults.adapter = () => Promise.reject({ message: 'x' })

      await expect(getDataStats()).rejects.toBeInstanceOf(Error)
    })
  })

  describe('searchStocks', () => {
    it('解包 res.data.stocks 直接返回数组', async () => {
      const stocks = [{ ts_code: '600000.SH', name: '浦发银行' }]
      vi.spyOn(http, 'get').mockResolvedValue({ data: { stocks } })

      const result = await searchStocks('浦发')

      expect(result).toEqual(stocks)
    })

    it('透传查询参数 q 与 limit', async () => {
      const getSpy = vi.spyOn(http, 'get').mockResolvedValue({ data: { stocks: [] } })

      await searchStocks('平安', 5)

      expect(getSpy).toHaveBeenCalledWith('/api/stocks/search', { params: { q: '平安', limit: 5 } })
    })
  })
})
