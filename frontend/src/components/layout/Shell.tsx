import { Outlet } from "react-router-dom";
import { BottomBar } from "./BottomBar";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

export function Shell() {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <Topbar />
        <main className="flex-1 p-6 overflow-auto pb-10">
          <Outlet />
        </main>
      </div>
      <BottomBar />
    </div>
  );
}
