import { useEffect, useState } from "react";

export default function Home() {
  const [status, setStatus] = useState({});
  const [results, setResults] = useState([]);
  const [keyword, setKeyword] = useState("");

  async function loadData() {
    const s = await fetch(
      "https://raw.githubusercontent.com/<USER>/<REPO>/main/crawler/crawl_status.json"
    ).then(r => r.json());

    const csv = await fetch(
      "https://raw.githubusercontent.com/<USER>/<REPO>/main/crawler/keyword_search_results.csv"
    ).then(r => r.text());

    setStatus(s);

    const rows = csv.split("\n").slice(1).map(r => r.split(","));
    setResults(rows);
  }

  async function saveKeyword() {
    await fetch("/api/save-keyword", {
      method: "POST",
      body: JSON.stringify({ keyword })
    });
    alert("Keyword saved. Trigger GitHub Action.");
  }

  useEffect(() => {
    loadData();
    const t = setInterval(loadData, 15000);
    return () => clearInterval(t);
  }, []);

  return (
    <main style={{ padding: 20 }}>
      <h1>🔍 Keyword Search Dashboard</h1>

      <input
        value={keyword}
        onChange={e => setKeyword(e.target.value)}
        placeholder="Enter keyword"
      />
      <button onClick={saveKeyword}>Save Keyword</button>

      <h3>Status: {status.state}</h3>
      <p>
        {status.processed}/{status.total_urls} processed | Found:{" "}
        {status.found}
      </p>

      <table border="1">
        <thead>
          <tr>
            <th>URL</th>
            <th>Type</th>
            <th>Found</th>
            <th>Details</th>
          </tr>
        </thead>
        <tbody>
          {results.map((r, i) => (
            <tr key={i}>
              <td>{r[0]}</td>
              <td>{r[1]}</td>
              <td>{r[2]}</td>
              <td>{r[3]}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}
