import { formatStratumLocation, PARAMETER_FIELD_LABELS } from './soilParameterDisplay'
import './SoilParameters.css'

/**
 * One page's classified/unclassified strata (POST /soil-parameters'
 * strata_results). Mirrors the visual grammar RuleCheckedFindings/
 * LabCrossReferenceFindings/JudgmentFindings already established (bold
 * primary "Where" label, muted secondary metadata, status-colored left
 * border) without sharing code with them - a classified stratum isn't a
 * pass/fail, it's a different kind of result, so it gets its own card
 * treatment (blue, not green) built for what it actually needs to show:
 * the classification basis, every warning, and per-field provisional
 * markers - none of which the rule-finding cards have a slot for.
 */
export default function SoilParameterFindings({ strataResults }) {
  if (!strataResults || strataResults.length === 0) {
    return <p className="soil-param-empty">No strata were extracted from this sheet.</p>
  }

  return (
    <ul className="soil-param-list">
      {strataResults.map((sr, i) => {
        const { classification, parameters } = sr
        const location = formatStratumLocation(sr.stratum)

        if (!classification.classified) {
          return (
            <li key={i} className="soil-param-card soil-param-card-unclassified">
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
          <li key={i} className="soil-param-card soil-param-card-classified">
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
                    <td className="soil-param-field-label">{PARAMETER_FIELD_LABELS[key] ?? key}</td>
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
                    <strong>{PARAMETER_FIELD_LABELS[key] ?? key} is provisional:</strong> {f.source_note}
                  </li>
                ))}
              </ul>
            )}

            <p className="soil-param-table-source">Source: {parameters.table_source}</p>
          </li>
        )
      })}
    </ul>
  )
}
