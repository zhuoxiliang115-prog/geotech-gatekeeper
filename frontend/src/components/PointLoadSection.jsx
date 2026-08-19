import PointLoadTable from './PointLoadTable'

export default function PointLoadSection({ results }) {
  if (!results || results.length === 0) return null

  return (
    <section className="result-section">
      <h2>Point Load Strength Index ({results.length} readings)</h2>
      <p className="calc-explanation-text">
        Point Load testing estimates rock strength from a small core or lump sample by measuring
        the load needed to fracture it between two conical platens. The result is size-corrected
        (Is50) so results from different specimen sizes can be compared on the same basis:
        Is = P / De² (P = failure load in kN, De = equivalent core diameter in mm), then Is50 = Is
        × (De / 50)^0.45 corrects to a reference 50mm diameter. This report already includes the
        lab's own corrected Is50 - there's no core diameter printed on it to recompute from.
      </p>
      <PointLoadTable readings={results} />
    </section>
  )
}
