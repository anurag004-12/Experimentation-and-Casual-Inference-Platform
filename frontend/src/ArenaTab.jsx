import PeekingCard from "./arena/PeekingCard.jsx";

export default function ArenaTab() {
  return (
    <div>
      <p className="muted intro">
        Real data never tells you the true answer. These simulations do, so you can see which methods work and
        where they fail. Everything here runs on simulated data.
      </p>
      <PeekingCard />
    </div>
  );
}