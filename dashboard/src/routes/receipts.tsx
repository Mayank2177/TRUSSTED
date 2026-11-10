import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { AlertTriangle, CheckCircle2, ChevronDown, ChevronUp, Copy, FileCheck2, Fingerprint, Info, KeyRound, Upload } from "lucide-react";
import { useId } from "react";
import { Button } from "@/components/ui/button";
import { EvidenceStamp, PageHeader, StatusBadge } from "@/components/evidence";
import { receiptEvents } from "@/lib/evidence-data";

export const Route = createFileRoute("/receipts")({
  head: () => ({ meta: [
    { title: "Receipts · Trussted" },
    { name: "description", content: "Inspect a sample event receipt and see the current limitations of the illustrative verification panel." },
    { property: "og:title", content: "Receipts · Trussted" },
    { property: "og:description", content: "A sample decision event chain and a clearly labeled, unconnected verification panel." },
    { property: "og:type", content: "website" },
    { name: "twitter:card", content: "summary" },
  ] }),
  component: ReceiptsPage,
});

function ReceiptsPage() {
  const receiptId = useId();
  const keyId = useId();
  const [receiptFile, setReceiptFile] = useState<File | null>(null);
  const [keyFile, setKeyFile] = useState<File | null>(null);
  const [expanded, setExpanded] = useState("evt_004");
  const [copyState, setCopyState] = useState("");
  const [verifyRequested, setVerifyRequested] = useState(false);

  async function copyDigest(digest: string, eventId: string) {
    try {
      await navigator.clipboard.writeText(digest);
      setCopyState(eventId);
      window.setTimeout(() => setCopyState(""), 1600);
    } catch {
      setCopyState("unavailable");
    }
  }

  return <div>
    <PageHeader eyebrow="DECISION RECORDS" title="Receipts" description="Inspect an example event chain. Upload controls are present, but no cryptographic verifier is connected." actions={<EvidenceStamp />} />
    <section className="receipt-overview">
      <div className="receipt-overview-icon"><FileCheck2 aria-hidden="true" /></div>
      <div><p className="eyebrow">SAMPLE RECEIPT</p><h2>Decision record · S6 cross-page conflict</h2><p>4 example events · captured 2026-11-08 05:42 UTC</p></div>
      <span className="receipt-id mono-text">rcpt_01HX9M2V</span>
    </section>
    <section className="receipt-layout">
      <section className="receipt-chain" aria-labelledby="chain-heading">
        <div className="section-heading-row"><div><h2 id="chain-heading" className="section-title">Event chain</h2><p className="section-subtitle">Each event references the preceding digest.</p></div><Fingerprint aria-hidden="true" className="subtle-icon" /></div>
        <div className="timeline-list">
          {receiptEvents.map((event, index) => <article className={`timeline-event${event.status === "BLOCK" ? " timeline-event-broken" : ""}`} key={event.id}>
            <div className="timeline-track"><span className={`timeline-node${event.status === "BLOCK" ? " timeline-node-broken" : ""}`} aria-hidden="true">{event.status === "BLOCK" ? <AlertTriangle /> : <span>{index + 1}</span>}</span>{index < receiptEvents.length - 1 ? <span className={`timeline-connector${event.status === "BLOCK" ? " timeline-connector-broken" : ""}`} aria-hidden="true" /> : null}</div>
            <div className="timeline-content">
              <div className="event-header"><div><h3>{event.stage}</h3><span className="event-id mono-text">{event.id}</span></div><StatusBadge status={event.status} /></div>
              <p className="event-result">{event.result}</p>
              <Button variant="ghost" className="detail-trigger" aria-expanded={expanded === event.id} aria-controls={`event-detail-${event.id}`} onClick={() => setExpanded(expanded === event.id ? "" : event.id)}>
                {expanded === event.id ? <ChevronUp aria-hidden="true" /> : <ChevronDown aria-hidden="true" />}{expanded === event.id ? "Hide digest" : "View digest"}
              </Button>
              {expanded === event.id ? <div id={`event-detail-${event.id}`} className="event-digest">
                <div><span className="digest-label">EVENT DIGEST</span><code className="mono-text">{event.digest}</code><Button type="button" variant="ghost" size="icon" aria-label={`Copy ${event.id} digest`} onClick={() => copyDigest(event.digest, event.id)}><Copy aria-hidden="true" /></Button>{copyState === event.id ? <span className="copy-confirm" role="status">Copied</span> : null}</div>
                {index > 0 ? <p><span className="digest-label">PREVIOUS EVENT</span><code className="mono-text">{receiptEvents[index - 1]?.digest ?? "No prior event"}</code></p> : null}
              </div> : null}
            </div>
          </article>)}
        </div>
      </section>
      <aside className="verify-panel" aria-labelledby="verify-heading">
        <p className="eyebrow">RECEIPT INSPECTION</p><h2 id="verify-heading">Inspect a receipt</h2>
        <p className="verify-description">Choose a receipt and a public key. Files stay in this browser; the sample cannot be cryptographically verified here.</p>
        <div className="file-picker"><label htmlFor={receiptId}><FileCheck2 aria-hidden="true" /><span><strong>Receipt file</strong><small>{receiptFile?.name ?? "JSON or text receipt"}</small></span></label><input id={receiptId} type="file" accept="application/json,.json,.txt" onChange={(event) => setReceiptFile(event.target.files?.[0] ?? null)} /><Button type="button" variant="outline" asChild><label htmlFor={receiptId}><Upload aria-hidden="true" /> Choose file</label></Button></div>
        <div className="file-picker"><label htmlFor={keyId}><KeyRound aria-hidden="true" /><span><strong>Public key</strong><small>{keyFile?.name ?? "PEM public key"}</small></span></label><input id={keyId} type="file" accept=".pem,.pub,.txt" onChange={(event) => setKeyFile(event.target.files?.[0] ?? null)} /><Button type="button" variant="outline" asChild><label htmlFor={keyId}><Upload aria-hidden="true" /> Choose file</label></Button></div>
        <Button type="button" className="verify-button" onClick={() => setVerifyRequested(true)} disabled={!receiptFile || !keyFile}><Fingerprint aria-hidden="true" /> Inspect selected files</Button>
        {verifyRequested ? <div className="verify-result" role="status"><AlertTriangle aria-hidden="true" /><div><strong>Verification unavailable</strong><p>No cryptographic verifier is connected; no pass or fail result was produced.</p></div></div> : null}
        <div className="verify-limit"><Info aria-hidden="true" /><p>Example digest strings can illustrate a chain, but do not demonstrate that its links or signer are valid.</p></div>
      </aside>
    </section>
    <section className="receipt-integrity" aria-label="Sample chain result"><div><CheckCircle2 aria-hidden="true" /><span>Example events listed</span></div><div className="integrity-divider" aria-hidden="true" /><div><AlertTriangle aria-hidden="true" /><span>Digest link is illustrative, not verified</span></div></section>
  </div>;
}