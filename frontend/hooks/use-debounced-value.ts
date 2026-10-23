"use client"

import { useEffect, useState } from "react"

/** Trì hoãn giá trị `value` một khoảng `delay` ms — search input không giật
 * query server từng keystroke. */
export function useDebouncedValue<T>(value: T, delay = 300): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const id = window.setTimeout(() => setDebounced(value), delay)
    return () => window.clearTimeout(id)
  }, [value, delay])
  return debounced
}
