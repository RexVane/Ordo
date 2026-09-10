import type { MetadataRoute } from 'next'
import { ORDO_MARK_PATH } from '@/lib/brand'

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: 'Ordo',
    short_name: 'Ordo',
    description: 'Inspectable, replaceable, regression-tested enterprise RAG infrastructure',
    start_url: '/',
    display: 'standalone',
    background_color: '#f4fbff',
    theme_color: '#55c7f3',
    icons: [
      {
        src: ORDO_MARK_PATH,
        sizes: '512x512',
        type: 'image/png',
      },
    ],
  }
}
