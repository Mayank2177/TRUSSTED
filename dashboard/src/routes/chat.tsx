import { useState, type FormEvent } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { ArrowUpRight, Check, CornerDownLeft, Info, Minus, Plus, Send, ShoppingBag, SlidersHorizontal } from "lucide-react";
import { useId } from "react";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/evidence";
import daypackImage from "@/assets/sample-daypack.jpg";
import tumblerImage from "@/assets/sample-tumbler.jpg";
import runningLightImage from "@/assets/sample-running-light.jpg";

export const Route = createFileRoute("/chat")({
  head: () => ({ meta: [
    { title: "Shopping chat · Trussted" },
    { name: "description", content: "Explore a clearly labeled sample shopping conversation and illustrative product comparisons in Trussted." },
    { property: "og:title", content: "Shopping chat · Trussted" },
    { property: "og:description", content: "Explore illustrative product recommendations and their reference details." },
    { property: "og:type", content: "website" },
    { name: "twitter:card", content: "summary" },
  ] }),
  component: ShoppingChatPage,
});

type Message = { id: number; role: "user" | "assistant"; text: string };
const products = [
  { id: "pack", name: "Trail daypack · 18 L", price: "USD 48.00", detail: "Recycled nylon · 18-liter capacity · 620 g", image: daypackImage, source: "Example product page · listing 0182", comparison: "18 L stated on example listing; reference details are illustrative." },
  { id: "tumbler", name: "Insulated travel tumbler", price: "USD 24.00", detail: "Stainless steel · 475 ml · screw-top lid", image: tumblerImage, source: "Example product page · listing 0447", comparison: "475 ml stated on example listing; reference details are illustrative." },
  { id: "light", name: "Clip-on running light", price: "USD 19.00", detail: "USB-C rechargeable · 3 light modes · 42 g", image: runningLightImage, source: "Example product page · listing 0316", comparison: "USB-C charging stated on example listing; reference details are illustrative." },
];

function ShoppingChatPage() {
  const inputId = useId();
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([
    { id: 1, role: "user", text: "I need a small daypack for commuting. Please show me what you found." },
    { id: 2, role: "assistant", text: "Here are three sample listings to compare. Prices and product details are illustrative, not live offers. I’ll show the reference details alongside each item." },
  ]);
  const [bag, setBag] = useState<Record<string, number>>({});
  const [notice, setNotice] = useState("");
  const bagCount = Object.values(bag).reduce((sum, quantity) => sum + quantity, 0);
  const bagTotal = products.reduce((sum, item) => sum + (Number.parseFloat(item.price.replace("USD ", "")) * (bag[item.id] ?? 0)), 0);

  function sendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = input.trim();
    if (!text) return;
    setMessages((current) => [...current, { id: Date.now(), role: "user", text }, { id: Date.now() + 1, role: "assistant", text: "This is a local sample chat; no shopping service is connected. The three example listings remain available above for comparison." }]);
    setInput("");
  }

  function changeBag(id: string, delta: number) {
    setBag((current) => ({ ...current, [id]: Math.max(0, (current[id] ?? 0) + delta) }));
    setNotice(delta > 0 ? "Added to your sample order." : "Updated your sample order.");
  }

  return <div>
    <PageHeader eyebrow="SHOPPING ASSISTANT · DEMO" title="Shop together" description="Compare product details against example references, then build a sample order." />
    <div className="chat-layout">
      <section className="chat-column" aria-label="Shopping chat">
        <div className="chat-toolbar"><div><span className="chat-live-dot" aria-hidden="true" />Sample conversation</div><span className="mono-text">SHOP-EXAMPLE-01</span></div>
        <div className="chat-messages" aria-live="polite" aria-relevant="additions">
          {messages.map((message) => <article key={message.id} className={`chat-message chat-message-${message.role}`}>
            <span className="chat-avatar" aria-hidden="true">{message.role === "user" ? "Y" : "T"}</span>
            <div className="chat-message-content"><span className="chat-message-author">{message.role === "user" ? "You" : "Trussted · sample assistant"}</span><p>{message.text}</p></div>
          </article>)}
        </div>
        <form className="chat-composer" onSubmit={sendMessage}>
          <label htmlFor={inputId} className="sr-only">Message the sample shopping assistant</label>
          <input id={inputId} value={input} onChange={(event) => setInput(event.target.value)} placeholder="Ask about a product or detail…" className="chat-input" />
          <Button type="submit" aria-label="Send message" size="icon" className="min-h-11 min-w-11"><Send aria-hidden="true" /></Button>
        </form>
        <div className="chat-composer-foot"><span><CornerDownLeft aria-hidden="true" /> Local demo only</span><span>No store or agent is connected</span></div>
      </section>

      <aside className="shopping-aside" aria-label="Example products and sample order">
        <section className="product-section" aria-labelledby="listings-heading">
          <div className="section-heading-row"><div><h2 id="listings-heading" className="section-title">Example listings</h2><p className="section-subtitle">Details shown beside their sample reference.</p></div><SlidersHorizontal aria-hidden="true" className="subtle-icon" /></div>
          <div className="product-list">
            {products.map((product) => <article className="product-row" key={product.id}>
              <div className="product-image-frame"><img src={product.image} alt={product.name} loading="lazy" width={816} height={816} /></div>
              <div className="product-copy">
                <div className="product-title-row"><h3>{product.name}</h3><span className="product-price">{product.price}</span></div>
                <p className="product-specs">{product.detail}</p>
                <p className="product-reference"><Info aria-hidden="true" /> {product.comparison}</p>
                <div className="product-actions"><span className="source-tag">{product.source}</span><Button type="button" size="sm" variant={bag[product.id] ? "secondary" : "outline"} onClick={() => changeBag(product.id, 1)}><Plus aria-hidden="true" /> Add</Button></div>
              </div>
            </article>)}
          </div>
        </section>
        <section className="sample-order" aria-labelledby="order-heading">
          <div className="order-heading"><div><p className="eyebrow">LOCAL SAMPLE ONLY</p><h2 id="order-heading">Your order <span className="order-count">{bagCount}</span></h2></div><ShoppingBag aria-hidden="true" /></div>
          {bagCount === 0 ? <p className="order-empty">Your order is empty. Add a sample listing to compare a total.</p> : <>
            <div className="order-items">{products.filter((product) => bag[product.id]).map((product) => <div className="order-item" key={product.id}><div><strong>{product.name}</strong><span>{product.price}</span></div><div className="quantity-controls"><Button type="button" size="icon" variant="ghost" aria-label={`Remove one ${product.name}`} onClick={() => changeBag(product.id, -1)}><Minus aria-hidden="true" /></Button><span>{bag[product.id]}</span><Button type="button" size="icon" variant="ghost" aria-label={`Add one ${product.name}`} onClick={() => changeBag(product.id, 1)}><Plus aria-hidden="true" /></Button></div></div>)}</div>
            <div className="order-total"><span>Sample total · before tax</span><strong>USD {bagTotal.toFixed(2)}</strong></div>
            <Button type="button" className="order-continue" variant="outline" onClick={() => setNotice("No checkout is connected. Your sample order has not been placed.")}><Check aria-hidden="true" /> Review sample order</Button>
          </>}
          {notice ? <p className="order-notice" role="status">{notice}</p> : null}
          <p className="order-disclaimer"><Info aria-hidden="true" /> This sample order does not reserve items or process payment.</p>
        </section>
        <div className="browse-link"><span>Need a shopping decision trace?</span><a href="/#overview-heading">Return to example runs <ArrowUpRight aria-hidden="true" /></a></div>
      </aside>
    </div>
  </div>;
}