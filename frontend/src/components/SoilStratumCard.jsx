import { DESIGN_TABLE_FIELD_LABELS, formatStratumLocation } from './designParameterDisplay'
import './DesignParameters.css'

/**
 * One classified/unclassified soil stratum from POST /soil-parameters.
 * Extracted from what used to be SoilParameterFindings.jsx's per-item
 * body so the merged Design Parameters list (DesignParameterFindings.jsx)
 * can render soil and rock strata side by side in one depth-ordered list,
 * each with its own card component - unchanged markup/behaviour from
 * before the split, just no longer tied to iterating a soil-only array.
 */
export default function SoilStratumCard({ sr }) {
  const { classification, parameters } = sr
  const location = formatStratumLocation(sr.stratum)

  if (!classification.classified) {
    return (
      <li className="soil-param-card soil-param-card-unclassified">
        <div className="soil-param-head">
          <span className="soil-param-location">{location}</span>
          <span className="soil-param-status-label">Not classified</span>
        </div>
        <p className="soil-param-flag">
          {classification.flag}
          {classification.principal_soil_type && (
            <span className="soil-param-principal-hint"> (read as {classification.principal_soil_type})</span>
          )}
        </p>
      </li>
    )
  }

  const fieldEntries = Object.entries(parameters.fields)
  const notedFields = fieldEntries.filter(([, f]) => f.source_note)

  return (
    <li className="soil-param-card soil-param-card-classified">
      <div className="soil-param-head">
        <span className="soil-param-location">{location}</span>
        <span className="soil-param-bucket-label">
          {parameters.geological_unit} · {parameters.label}
        </span>
      </div>

      <p className="soil-param-basis">
        <strong>Classified as:</strong> {classification.classification_basis}
      </p>

      {classification.warnings.length > 0 && (
        <ul className="soil-param-warnings">
          {classification.warnings.map((w, wi) => (
            <li key={wi} className="soil-param-warning">
              <span className="soil-param-warning-icon" aria-hidden="true">⚠</span> {w}
            </li>
          ))}
        </ul>
      )}

      <table className="soil-param-fields">
        <tbody>
          {fieldEntries.map(([key, f]) => (
            <tr key={key} className={f.source_note ? 'soil-param-field-provisional' : undefined}>
              <td className="soil-param-field-label">{DESIGN_TABLE_FIELD_LABELS[key] ?? key}</td>
              <td className="soil-param-field-value">
                {f.value ?? '—'}
                {f.value != null && f.unit && f.unit !== '-' ? ` ${f.unit}` : ''}
                {f.source_note && (
                  <span
                    className="soil-param-provisional-badge"
                    title={f.source_note}
                    aria-label={`Provisional value: ${f.source_note}`}
                  >
                    ⚠ provisional
                  </span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {notedFields.length > 0 && (
        <ul className="soil-param-notes">
          {notedFields.map(([key, f]) => (
            <li key={key} className="soil-param-note">
              <strong>{DESIGN_TABLE_FIELD_LABELS[key] ?? key} is provisional:</strong> {f.source_note}
            </li>
          ))}
        </ul>
      )}

      <p className="soil-param-table-source">Source: {parameters.table_source}</p>
    </li>
  )
}
