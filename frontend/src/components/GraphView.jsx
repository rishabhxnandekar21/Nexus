import { useEffect, useMemo, useRef } from 'react'
import CytoscapeComponent from 'react-cytoscapejs'

import Notice from './Notice'

/**
 * The Cytoscape canvas - F3, plus the F5 analytics encodings.
 *
 * Entity type is encoded twice, by SHAPE and by COLOUR, and the shape is the
 * one that actually carries it. Six categories cannot be told apart by hue:
 * the palette validator scores the best available six-hue set at worst-pair
 * ΔE 1.6 for deuteranopia and 10.6 for normal vision, against floors of 8 and
 * 15. Colour at six categories is decoration. Shape, the always-on label and
 * the legend are what make a node identifiable, including in greyscale and
 * for a colourblind viewer.
 *
 * Shape stays bound to entity type even when colour switches to community, so
 * switching the colour encoding never costs you the type.
 */

const TYPES = {
  person: { colour: '#3987e5', shape: 'ellipse', label: 'Person' },
  vehicle: { colour: '#d95926', shape: 'round-rectangle', label: 'Vehicle' },
  phone: { colour: '#199e70', shape: 'diamond', label: 'Phone' },
  location: { colour: '#c98500', shape: 'triangle', label: 'Location' },
  organization: { colour: '#d55181', shape: 'hexagon', label: 'Organisation' },
  crime_event: { colour: '#008300', shape: 'star', label: 'Crime event' },
}
const UNKNOWN = '#94a3b8'

// Four hues, not more: this set is the largest that clears the validator on
// this surface for all pairs (worst normal-vision ΔE 19.3). Communities have
// no shape to fall back on, so the count is capped rather than the contrast.
// Everything outside the four largest communities is grey and labelled so.
const COMMUNITY_COLOURS = ['#3987e5', '#c98500', '#d55181', '#008300']
const COMMUNITY_OTHER = '#64748b'

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
      // on-screen size, so labels appear as you zoom into a region.
      'min-zoomed-font-size': 9,
      // Colour and size are computed in JS and carried on the element, so the
      // encoding can change without swapping the stylesheet - which would
      // remount the graph and re-run the layout.
      'background-color': 'data(_colour)',
      width: 'data(_size)',
      height: 'data(_size)',
      'border-width': 2,
      'border-color': '#0f172a',
    },
  },
  ...Object.entries(TYPES).map(([type, { shape }]) => ({
    selector: `node[entity_type = "${type}"]`,
    style: { shape },
  })),
  {
    // Shared across agencies - a dashed ring, so it is not colour-only either.
    selector: 'node[?is_shared]',
    style: { 'border-color': '#e2e8f0', 'border-style': 'dashed' },
  },
  { selector: 'node.selected', style: { 'border-color': '#f8fafc', 'border-width': 4 } },
  { selector: 'node.centre', style: { 'border-color': '#38bdf8', 'border-width': 4 } },
  { selector: 'node.on-path', style: { 'border-color': '#fbbf24', 'border-width': 5 } },
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
    selector: 'edge.on-path',
    style: { 'line-color': '#fbbf24', 'target-arrow-color': '#fbbf24', width: 4 },
  },
  { selector: 'edge[?predicted]', style: { 'line-style': 'dashed', 'line-color': '#7c8da5' } },
]

const LAYOUT = {
  name: 'cose',
  animate: false,
  padding: 40,
  nodeRepulsion: 12000,
  idealEdgeLength: 110,
  nodeDimensionsIncludeLabels: true,
}

const SIZE_MIN = 26
const SIZE_MAX = 62

export default function GraphView({
  elements,
  metrics,
  colourBy = 'type',
  sizeBy = 'degree',
  topCommunities = [],
  pathIds = [],
  selectedId,
  centerId,
  onSelect,
  onRecentre,
}) {
  const cyRef = useRef(null)

  const memoElements = useMemo(() => {
    const rank = new Map(topCommunities.map((c, i) => [c, i]))
    const values = elements.nodes.map((n) => metricValue(metrics, n.data.id, sizeBy, n.data.degree))
    const highest = Math.max(1, ...values)

    const nodes = elements.nodes.map((n) => {
      const metric = metrics?.get?.(Number(n.data.id))
      const value = metricValue(metrics, n.data.id, sizeBy, n.data.degree)
      const colour =
        colourBy === 'community'
          ? (rank.has(metric?.community)
              ? COMMUNITY_COLOURS[rank.get(metric.community)]
              : COMMUNITY_OTHER)
          : (TYPES[n.data.entity_type]?.colour ?? UNKNOWN)
      return {
        data: {
          ...n.data,
          _colour: colour,
          // Square-rooted so one hub does not flatten everything else to a dot.
          _size: SIZE_MIN + (SIZE_MAX - SIZE_MIN) * Math.sqrt(value / highest),
        },
      }
    })
    return [...nodes, ...elements.edges]
  }, [elements, metrics, colourBy, sizeBy, topCommunities])

  useEffect(() => {
    const cy = cyRef.current
    if (!cy) return
    cy.elements().removeClass('selected centre on-path')
    if (selectedId != null) cy.getElementById(String(selectedId)).addClass('selected')
    if (centerId != null) cy.getElementById(String(centerId)).addClass('centre')
    if (pathIds.length > 1) {
      pathIds.forEach((id) => cy.getElementById(String(id)).addClass('on-path'))
      for (let i = 0; i < pathIds.length - 1; i += 1) {
        cy.edges().filter((e) => {
          const pair = [e.data('source'), e.data('target')].map(Number)
          return pair.includes(pathIds[i]) && pair.includes(pathIds[i + 1])
        }).addClass('on-path')
      }
    }
  }, [selectedId, centerId, pathIds, memoElements])

  function register(cy) {
    if (cyRef.current === cy) return
    cyRef.current = cy
    cy.on('tap', 'node', (event) => onSelect(Number(event.target.id())))
    cy.on('dbltap', 'node', (event) => onRecentre(Number(event.target.id())))
    cy.on('tap', (event) => {
      if (event.target === cy) onSelect(null)
    })
    // cose finishes before the container has necessarily settled at its final
    // size, which leaves the network bunched in one corner. Fit once it stops.
    cy.on('layoutstop', () => cy.fit(undefined, 40))
  }

  if (memoElements.length === 0) {
    return (
      <Notice tone="empty" title="Nothing to draw" className="h-[32rem]">
        No entities match. Widen the year range, clear the search, or show the
        whole network.
      </Notice>
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
      {colourBy === 'community' ? (
        <CommunityLegend count={topCommunities.length} />
      ) : (
        <TypeLegend />
      )}
      <p className="mt-2 text-xs text-slate-500">
        Click a node for its details. Double-click to re-centre on it. Shape is
        always the entity type; node size is {sizeBy}.
      </p>
    </div>
  )
}

function metricValue(metrics, id, sizeBy, fallbackDegree) {
  const metric = metrics?.get?.(Number(id))
  if (!metric) return sizeBy === 'degree' ? (fallbackDegree ?? 0) : 0
  return metric[sizeBy] ?? 0
}

function TypeLegend() {
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
          <circle cx="7" cy="7" r="5" fill="none" stroke="#e2e8f0" strokeWidth="1.5" strokeDasharray="2 2" />
        </svg>
        Shared across agencies
      </li>
    </ul>
  )
}

function CommunityLegend({ count }) {
  return (
    <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-2" aria-label="Communities">
      {COMMUNITY_COLOURS.slice(0, count).map((colour, i) => (
        <li key={colour} className="flex items-center gap-1.5 text-xs text-slate-400">
          <svg width="14" height="14" aria-hidden="true">
            <circle cx="7" cy="7" r="5.5" fill={colour} />
          </svg>
          Community {i + 1}
        </li>
      ))}
      <li className="flex items-center gap-1.5 text-xs text-slate-400">
        <svg width="14" height="14" aria-hidden="true">
          <circle cx="7" cy="7" r="5.5" fill={COMMUNITY_OTHER} />
        </svg>
        All other communities
      </li>
      <li className="text-xs text-slate-500">Shape still shows the entity type.</li>
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
      {shapes[type] ?? <circle cx="7" cy="7" r="5.5" fill={UNKNOWN} />}
    </svg>
  )
}
