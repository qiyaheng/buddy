import type { WbApi } from './index'

declare global {
  interface Window {
    wb: WbApi
  }
}

export {}
