import { DESIGN_TABLE_FIELD_LABELS, formatStratumLocation } from './designParameterDisplay'
import { HOEK_BROWN_FIELD_LABELS, strengthConfidenceLabel } from './rockParameterDisplay'
import './DesignParameters.css'

/**
 * One field-labelled table for one reference table (design_table or
 * hoek_brown_table), with its own heading, one-line explainer, and
 * per-field provisional badges - kept as its own block rather than
 * merged with the other table, mirroring the same "don't merge two
 * different lenses on the same rock" decision already made in
 * rock_typical_parameters.json/lookup.py itself.
 */
function ParameterBlock({ title, note, table, labels }) {
  const fieldEntries = Object.entries(table.fields)
  const notedFields = fieldEntries.filter(([, f]) => f.source_note)

  return (
    <div className="design-param-block">
      <p className="design-param-block-title">{title}</p>
      <p className="design-param-block-note">{note}</p>

      <table className="soil-param-fields">
        <tbody>
          {fieldEntries.map(([key, f]) => (
            <tr key={key} className={f.source_note ? 'soil-param-field-provisional' : undefined}>
              <td className="soil-param-field-label">{labels[key] ?? key}</td>
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
              <strong>{labels[key] ?? key} is provisional:</strong> {f.source_note}
            </li>
          ))}
        </ul>
      )}

      <p className="soil-param-table-source">Source: {table.table_source}</p>
    </div>
  )
}

/**
 * One classified/unclassified rock stratum from POST /rock-parameters.
 * Mirrors SoilStratumCard's grammar (same .soil-param-* card, head,
 * basis, warnings classes) rather than reinventing it, since a
 * classified stratum is a classified stratum whichever endpoint produced
 * it - the differences are additive: a confidence tag next to the bucket
 * label (Is(50) estimation is the norm here, not an edge case), a
 * spacing_basis line stating which sub-path (stated on the log vs
 * computed from defect depths) produced the governing spacing, and two
 * separate parameter blocks instead of one.
 */
export default function RockStratumCard({ sr }) {
  const { classification, parameters } = sr
  const location = formatStratumLocation(sr.stratum)

  if (!classification.classified) {
    return (
      <li className="soil-param-card soil-param-card-unclassified">
        <div className="soil-param-head">
          <span className="soil-param-location">{location}</span>
          <span className="soil-param-status-label">Not classified</span>
        </div>
        <p className="soil-param-flag">{classification.flag}</p>
      </li>
    )
  }

  const confidenceLabel = strengthConfidenceLabel(classification.strength)
  const isEstimated = classification.strength?.source === 'is50_estimated'

  return (
    <li className="soil-param-card soil-param-card-classified">
      <div className="soil-param-head">
        <span className="soil-param-location">{location}</span>
        <span>
          <span className="soil-param-bucket-label">
            {parameters.geological_unit} · {parameters.design_table.label}
          </span>
          {confidenceLabel && (
            <span
              className={isEstimated ? 'design-param-confidence-tag' : 'design-param-confidence-tag-measured'}
            >
              {confidenceLabel}
            </span>
          )}
        </span>
      </div>

      <p className="soil-param-basis">
        <strong>Classified as:</strong> {classification.classification_basis}
      </p>

      {classification.spacing_basis && (
        <p className="design-param-spacing-basis">
          <strong>Spacing:</strong> {classification.spacing_basis}
        </p>
      )}

      {classification.warnings.length > 0 && (
        <ul className="soil-param-warnings">
          {classification.warnings.map((w, wi) => (
            <li key={wi} className="soil-param-warning">
              <span className="soil-param-warning-icon" aria-hidden="true">⚠</span> {w}
            </li>
          ))}
        </ul>
      )}

      <ParameterBlock
        title="Design Parameters"
        note="Standard geotechnical design values for footings, piles and anchors."
        table={parameters.design_table}
        labels={DESIGN_TABLE_FIELD_LABELS}
      />

      <ParameterBlock
        title="Rock Mass (Hoek-Brown)"
        note="Hoek-Brown strength/stiffness parameters for numerical rock-mass modelling — a different lens on the same rock, not a second attempt at the design table's numbers."
        table={parameters.hoek_brown_table}
        labels={HOEK_BROWN_FIELD_LABELS}
      />
    </li>
  )
}
