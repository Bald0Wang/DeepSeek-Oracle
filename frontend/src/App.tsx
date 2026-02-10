import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { Layout } from "./components/Layout";
import DetailPage from "./pages/Detail";
import HistoryPage from "./pages/History";
import HomePage from "./pages/Home";
import LoadingPage from "./pages/Loading";
import OracleChatPage from "./pages/OracleChat";
import ResultPage from "./pages/Result";


export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<HomePage />} />
          <Route path="/oracle" element={<OracleChatPage />} />
          <Route path="/loading/:taskId" element={<LoadingPage />} />
          <Route path="/result/:id" element={<ResultPage />} />
          <Route path="/result/:id/:type" element={<DetailPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
