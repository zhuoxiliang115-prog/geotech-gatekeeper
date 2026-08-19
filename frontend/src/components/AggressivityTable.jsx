import { useState } from 'react'
import { as2159ConcreteClass, as2159SteelClass } from '../calculations'
import './AggressivityTable.css'

/**
 * AS 2159 durability classification table (spec chart 7). Soil Condition
 * A/B isn't auto-detected - the spec is explicit that it depends on soil
 * permeability and groundwater depth, data this app doesn't have yet, so
 * it's a manual per-sample selector here. Until it's set, the governing
 * class is left blank rather than guessing a default.
 *
 * All sample records here come from soil COA results (both ALS and
 * Envirolab reports in this batch were soil samples), so sulfate/chloride
 * map to the tables' soil columns; there's no groundwater sample data to
 * populate the groundwater columns.
 */
export default function AggressivityTable({ samples }) {
  const [conditions, setConditions] = useState({})

  const setCondition = (key, value) => {
    setConditions((prev) => ({ ...prev, [key]: value || null }))
  }

  return (
    <div className="table-scroll">
      <table className="aggressivity-table">
        <thead>
          <tr>
            <th>Sample</th>
            <th>pH</th>
            <th>SO4 (mg/kg)</th>
            <th>Cl (mg/kg)</th>
            <th>Resistivity (ohm·cm)</th>
            <th>Soil Condition</th>
            <th>Concrete class</th>
            <th>Steel class</th>
          </tr>
        </thead>
        <tbody>
          {samples.map((s, i) => {
            const key = s.mg_sample_no ?? s.lab_reference ?? s.sample_id ?? i
            const condition = conditions[key] ?? null

            const concreteClass = condition
              ? as2159ConcreteClass(condition, {
                  ph: s.ph,
                  sulfateSoilPpm: s.sulfate_mg_kg,
                })
              : null
            const steelClass = condition
              ? as2159SteelClass(condition, {
                  ph: s.ph,
                  chlorideSoilPpm: s.chloride_mg_kg,
                  resistivityOhmCm: s.resistivity_ohm_cm,
                })
              : null

            return (
              <tr key={key}>
                <td>{s.sample_id ?? s.mg_sample_no ?? '—'}</td>
                <td>{s.ph ?? '—'}</td>
                <td>{s.sulfate_mg_kg ?? (s.sulfate_mg_kg_below_lor != null ? `<${s.sulfate_mg_kg_below_lor}` : '—')}</td>
                <td>{s.chloride_mg_kg ?? (s.chloride_mg_kg_below_lor != null ? `<${s.chloride_mg_kg_below_lor}` : '—')}</td>
                <td>{s.resistivity_ohm_cm ?? '—'}</td>
                <td>
                  <select value={condition ?? ''} onChange={(e) => setCondition(key, e.target.value)}>
                    <option value="">— select —</option>
                    <option value="A">A (permeable, in groundwater)</option>
                    <option value="B">B (low permeability / above groundwater)</option>
                  </select>
                </td>
                <td>{concreteClass ?? (condition ? '—' : 'set condition')}</td>
                <td>{steelClass ?? (condition ? '—' : 'set condition')}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
