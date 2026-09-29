import { useEffect, useMemo, useRef } from 'react'
import CytoscapeComponent from 'react-cytoscapejs'

/**
 * The Cytoscape canvas - F3.
 *
 * Entity type is encoded twice, by SHAPE and by COLOUR, and the shape is the
 * one that actually carries it. Six categories cannot be told apart by hue:
 * the palette validator scores the best available six-hue set at worst-pair
 * ΔE 1.6 for deuteranopia and 10.6 for normal vision, against floors of 8 and
 * 15. Colour at six categories is decoration. Shape, the always-on label and
 * the legend are what make a node identifiable, including in greyscale and
 * for a colourblind viewer. Colours are the dark-surface steps of the
 * reference categorical palette, all >= 3:1 against this canvas.
 */

const TYPES = {
  person: { colour: '#3987e5', shape: 'ellipse', label: 'Person' },
  vehicle: { colour: '#d95926', shape: 'round-rectangle', label: 'Vehicle' },
  phone: { colour: '#199e70', shape: 'diamond', label: 'Phone' },
  location: { colour: '#c98500', shape: 'triangle', label: 'Location' },
  organization: { colour: '#d55181', shape: 'hexagon', label: 'Organisation' },
  crime_event: { colour: '#008300', shape: 'star', label: 'Crime event' },
}
const FALLBACK = { colour: '#94a3b8', shape: 'ellipse', label: 'Other' }

// Module-level, per CLAUDE.md Section 8: a new object identity on every render
// makes react-cytoscapejs rebuild the graph and visibly re-shuffle the layout.
const STYLESHEET = [
  {
    selector: 'node',
    style: {
      label: 'data(label)',
      'font-size': 11,
      color: '#e2e8f0',
      'text-outline-color': '#0f172a',
      'text-outline-width': 2,
      'text-valign': 'bottom',
      'text-margin-y': 4,
      // Whole-network views run to hundreds of nodes and every label drawn at
      // once is an unreadable smear. Cytoscape drops the label below this
      // on-screen size, so labels appear as you zoom into a region and the
      // overview stays a shape you can actually read.
      'min-zoomed-font-size': 9,
      // Degree drives size, per the F3 acceptance criteria.
      width: 'mapData(degree, 0, 8, 26, 62)',
      height: 'mapData(degree, 0, 8, 26, 62)',
      'border-width': 2,
      'border-color': '#0f172a',
    },
  },
  ...Object.entries(TYPES).map(([type, { colour, shape }]) => ({
    selector: `node[entity_type = "${type}"]`,
    style: { 'background-color': colour, shape },
  })),
  {
    // Shared across agencies - a dashed ring, so it is not colour-only either.
    selector: 'node[?is_shared]',
    style: { 'border-color': '#e2e8f0', 'border-style': 'dashed', 'border-width': 2 },
  },
  {
    selector: 'node.selected',
    style: { 'border-color': '#f8fafc', 'border-width': 4, 'border-style': 'solid' },
  },
  {
    selector: 'node.centre',
    style: { 'border-color': '#38bdf8', 'border-width': 4, 'border-style': 'solid' },
  },
  {
    selector: 'edge',
    style: {
      label: 'data(label)',
      'font-size': 8,
      'min-zoomed-font-size': 10,
      color: '#94a3b8',
      'text-outline-color': '#0f172a',
      'text-outline-width': 2,
      width: 1.5,
      'line-color': '#475569',
      'target-arrow-color': '#475569',
      'target-arrow-shape': 'triangle',
      'arrow-scale': 0.7,
      'curve-style': 'bezier',
    },
  },
  {
    selector: 'edge[?predicted]',
    style: { 'line-style': 'dashed', 'line-color': '#7c8da5' },
  },
]

const LAYOUT = {
  name: 'cose',
  animate: false,
  padding: 40,
  nodeRepulsion: 12000,
  idealEdgeLength: 110,
  nodeDimensionsIncludeLabels: true,
}

export default function GraphView({ elements, selectedId, centerId, onSelect, onRecentre }) {
  const cyRef = useRef(null)

  // Identity only changes when the data does, so the layout does not re-run on
  // every parent render.
  const memoElements = useMemo(
    () => [...elements.nodes, ...elements.edges],
    [elements],
  )

  useEffect(() => {
    const cy = cyRef.current
    if (!cy) return
    cy.nodes().removeClass('selected centre')
    if (selectedId != null) cy.getElementById(String(selectedId)).addClass('selected')
    if (centerId != null) cy.getElementById(String(centerId)).addClass('centre')
  }, [selectedId, centerId, memoElements])

  function register(cy) {
    if (cyRef.current === cy) return
    cyRef.current = cy
    cy.on('tap', 'node', (event) => onSelect(Number(event.target.id())))
    cy.on('dbltap', 'node', (event) => onRecentre(Number(event.target.id())))
    // Tapping the background clears the panel.
    cy.on('tap', (event) => {
      if (event.target === cy) onSelect(null)
    })
    // cose finishes before the container has necessarily settled at its final
    // size, which leaves the network bunched in one corner. Fit once it stops.
    cy.on('layoutstop', () => cy.fit(undefined, 40))
  }

  if (memoElements.length === 0) {
    return (
      <div className="flex h-[32rem] items-center justify-center rounded-lg border border-dashed border-slate-600 bg-slate-900">
        <p className="text-sm text-slate-400">
          No entities match. Widen the date range, or clear the search.
        </p>
      </div>
    )
  }

  return (
    <div>
      <div className="h-[32rem] overflow-hidden rounded-lg border border-slate-700 bg-slate-900">
        <CytoscapeComponent
          elements={memoElements}
          stylesheet={STYLESHEET}
          layout={LAYOUT}
          cy={register}
          style={{ width: '100%', height: '100%' }}
          wheelSensitivity={0.2}
        />
      </div>
      <Legend />
      <p className="mt-2 text-xs text-slate-500">
        Click a node for its details. Double-click to re-centre the graph on it.
        Node size is its number of connections.
      </p>
    </div>
  )
}

function Legend() {
  return (
    <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-2" aria-label="Node types">
      {Object.entries(TYPES).map(([type, { colour, label }]) => (
        <li key={type} className="flex items-center gap-1.5 text-xs text-slate-400">
          <ShapeSwatch type={type} colour={colour} />
          {label}
        </li>
      ))}
      <li className="flex items-center gap-1.5 text-xs text-slate-400">
        <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true">
          <circle
            cx="7" cy="7" r="5" fill="none"
            stroke="#e2e8f0" strokeWidth="1.5" strokeDasharray="2 2"
          />
        </svg>
        Shared across agencies
      </li>
    </ul>
  )
}

/** The legend must show the shape, since shape is what carries the type. */
function ShapeSwatch({ type, colour }) {
  const shapes = {
    person: <circle cx="7" cy="7" r="5.5" fill={colour} />,
    vehicle: <rect x="1.5" y="3" width="11" height="8" rx="2" fill={colour} />,
    phone: <path d="M7 1 L13 7 L7 13 L1 7 Z" fill={colour} />,
    location: <path d="M7 1.5 L13 12.5 L1 12.5 Z" fill={colour} />,
    organization: <path d="M4 1.8 h6 l3 5.2 -3 5.2 h-6 l-3 -5.2 Z" fill={colour} />,
    crime_event: (
      <path
        d="M7 1 L8.6 5.4 L13.2 5.5 L9.5 8.2 L10.9 12.7 L7 10 L3.1 12.7 L4.5 8.2 L0.8 5.5 L5.4 5.4 Z"
        fill={colour}
      />
    ),
  }
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true">
      {shapes[type] ?? <circle cx="7" cy="7" r="5.5" fill={FALLBACK.colour} />}
    </svg>
  )
}
