/**
 * Product image for an order line. There are no real product photos: known dosage
 * types get a generic, unbranded illustration of that product type (generated with
 * Canva AI); anything else gets a neutral medicine-bottle icon. Both carry the
 * line's label ("Product 1", ...).
 */
const TYPE_IMAGES: Record<string, string> = {
  herbdried: 'products/herb-dried.jpg',
  inhalation: 'products/inhalation.jpg',
  oralliquid: 'products/oral-liquid.jpg',
}

function imageFor(dosageType: string | null | undefined): string | null {
  if (!dosageType) return null
  const key = dosageType.toLowerCase().replace(/[^a-z]/g, '') // "Herb,dried" / "Herb, dried" -> "herbdried"
  const path = TYPE_IMAGES[key]
  return path ? `${import.meta.env.BASE_URL}${path}` : null
}

export function ProductPlaceholder({ label, dosageType }: { label: string; dosageType?: string | null }) {
  const src = imageFor(dosageType)
  if (src) {
    return (
      <figure className="product-ph product-ph--image">
        <img src={src} alt={`Generic ${dosageType?.toLowerCase()} product image (not the actual product)`} loading="lazy" />
        <figcaption>{label}</figcaption>
      </figure>
    )
  }
  return (
    <figure className="product-ph" aria-label={`${label} image placeholder`}>
      <svg viewBox="0 0 40 48" width="28" height="34" aria-hidden="true" focusable="false">
        <rect x="11" y="2" width="18" height="8" rx="2" fill="currentColor" opacity="0.55" />
        <rect x="13" y="10" width="14" height="3" fill="currentColor" opacity="0.35" />
        <rect x="6" y="13" width="28" height="33" rx="5" fill="none" stroke="currentColor" strokeWidth="2.2" />
        <rect x="10" y="22" width="20" height="14" rx="1.5" fill="currentColor" opacity="0.18" />
        <path d="M20 25.5v7M16.5 29h7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      </svg>
      <figcaption>{label}</figcaption>
    </figure>
  )
}
