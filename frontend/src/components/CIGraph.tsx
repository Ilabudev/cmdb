import cytoscape from "cytoscape";
import { useEffect, useRef } from "react";

export interface GraphData {
  nodes: { id: string; name: string; type_code: string; status: string; depth: number }[];
  edges: { id: string; type_code: string; source_id: string; target_id: string }[];
}

// FR-11: интерактивный граф зависимостей (данные — GET /cis/{id}/graph)
export default function CIGraph({ data, onSelect }: { data: GraphData; onSelect?: (id: string) => void }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current) return;
    const cy = cytoscape({
      container: ref.current,
      elements: [
        ...data.nodes.map((n) => ({ data: { id: n.id, label: n.name, type: n.type_code } })),
        ...data.edges.map((e) => ({
          data: { id: e.id, source: e.source_id, target: e.target_id, label: e.type_code },
        })),
      ],
      layout: { name: "breadthfirst", directed: true },
      style: [
        { selector: "node", style: { label: "data(label)", "font-size": 10 } },
        {
          selector: "edge",
          style: { label: "data(label)", "font-size": 8, "curve-style": "bezier", "target-arrow-shape": "triangle" },
        },
      ],
    });
    cy.on("tap", "node", (evt) => onSelect?.(evt.target.id()));
    return () => cy.destroy();
  }, [data, onSelect]);

  return <div ref={ref} style={{ width: "100%", height: 500 }} />;
}
