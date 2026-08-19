import AggressivityTable from './AggressivityTable'
import SalinityChart from './SalinityChart'

export default function ChemicalCoaSection({ results }) {
  if (!results || results.length === 0) return null

  return (
    <>
      <section className="result-section">
        <h2>AS 2159 Durability Classification ({results.length} samples)</h2>
        <p className="calc-explanation-text">
          This classifies how aggressive the soil and groundwater environment is toward buried
          concrete and steel piles, based on acidity, sulfate and chloride content, and electrical
          resistivity - per AS 2159-2009. Soil Condition A/B isn't auto-detected (it depends on
          soil permeability and groundwater depth, which needs borehole log data not wired up
          yet) - set it per sample below.
        </p>
        <AggressivityTable samples={results} />
      </section>

      <section className="result-section">
        <h2>Soil Salinity (ECe) ({results.length} samples)</h2>
        <p className="calc-explanation-text">
          This estimates the salinity of the soil (ECe) from a quick conductivity test (EC 1:5),
          adjusted for soil texture using a standard multiplication factor. Salinity affects plant
          growth, concrete durability, and corrosion risk. MF is entered manually per sample below
          using the Table 6.1 texture description - it reflects a field/visual soil assessment,
          not something derivable from lab numbers.
        </p>
        <SalinityChart samples={results} />
      </section>
    </>
  )
}
