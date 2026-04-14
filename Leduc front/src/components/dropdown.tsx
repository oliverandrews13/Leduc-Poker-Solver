"use client"
const Dropdown = ({playerNum}) => {

    const changeCard = async (card:string) =>
    {
        await fetch("/SetCard",
        {
            method:"POST",
            headers: {
                        "Content-Type": "application/json"
                    },
            body: JSON.stringify({ player: "" + playerNum, cardID: card })
        }
        );

    }
    return (
        <select onChange={(e) => changeCard(e.target.value)} className="rounded-lg bg-red-200 text-black">
            <option value="J">J</option>
            <option value="Q">Q</option>
            <option value="K">K</option>
        </select>
    )
}

export default Dropdown;
