"use client"

import { useEffect, useState } from "react"

/**
 * State nhỏ persist vào localStorage theo `key` (column visibility, page
 * size…). Giống pattern cũ ở trang feedbacks: SSR/hydrate render mặc định,
 * đọc storage SAU mount để không lệch hydration; storage bị chặn (private
 * mode) thì dùng trong phiên.
 *
 * `parse` ném lỗi hoặc trả `null` ⇒ rơi về `initialValue`.
 */
export function useStoredState<T>(
  key: string,
  initialValue: T,
  parse: (raw: string) => T | null,
): [T, (next: T) => void] {
  const [value, setValue] = useState<T>(initialValue)
  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(key)
      if (raw != null) {
        const parsed = parse(raw)
        // eslint-disable-next-line react-hooks/set-state-in-effect -- localStorage chỉ đọc sau mount, tránh lệch hydration SSR
        if (parsed != null) setValue(parsed)
      }
    } catch {
      // storage bị chặn — giữ default
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- chỉ chạy 1 lần sau mount
  }, [key])

  function set(next: T) {
    setValue(next)
    try {
      window.localStorage.setItem(key, JSON.stringify(next))
    } catch {
      // private mode… — vẫn đổi tạm trong phiên
    }
  }

  return [value, set]
}
