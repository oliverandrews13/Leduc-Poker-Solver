import Dropdown from "./components/dropdown";
import InfoCard from "./components/cards";
export function Sidebar()
{
  return (
    
    <div className="fixed inset left-0 top-0 w-[20%] min-w-54 h-full bg-linear-to-r from-gray-900 to-slate-900 ">
      <div className="flex flex-col justify-self-center text-2xl pt-[15%] text-white">Leduc Poker Solver </div>
      <div className="flex flex-col justify-self-center text-lg pt-[30%] w-[75%]">
          <div className="text-aling-left text-bold font-bold pt-5 text-white"> Player 0 Card</div>
          <Dropdown playerNum={0}></Dropdown>
      </div>
      <div className="flex flex-col justify-self-center text-lg pt-4 w-[75%]">
          <div className="text-aling-left text-bold font-bold pt-5 text-white"> Player 1 Card</div>
          <Dropdown playerNum={1}></Dropdown>
      </div>
    </div> 
  );
}

export default function Home() {
  return (
    <div className="h-screen relative">
             <Sidebar />
    <div className="absolute right-0 font-sans h-full w-[80%] content-stretch bg-amber-950">
    <div className="grid h-60 w-[30%] grid-cols-2  gap-3 absolute top-15 right-5"> 
      <InfoCard title={"street"} text={"Preflop"} />
      <InfoCard title={"street"} text={"Preflop"} />
      <InfoCard title={"street"} text={"Preflop"} />
      <InfoCard title={"street"} text={"Preflop"} />
      <InfoCard title={"street"} text={"Preflop"} />
      <InfoCard title={"street"} text={"Preflop"} />
    </div>
    </div>
    </div>
  );
}
