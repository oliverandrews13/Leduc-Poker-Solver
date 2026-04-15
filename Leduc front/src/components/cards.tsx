export default function InfoCard({title, text}){
    return (
        <div className="flex flex-col bg-gray-700/40 rounded-lg border-white border-2 h-18 relative">
            <div className="text-gray-400 text-sm flex flex-col pl-4">{title}</div>
            <div className="absolute bottom-1 left-1 text-white text-xl flex flex-col pl-4 ">{text}</div>
        </div>
    );
}