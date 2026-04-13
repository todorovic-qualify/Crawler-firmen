// Lead-Detailseite (wird in Step 4 implementiert)
export default function LeadDetailSeite({ params }: { params: { id: string } }) {
  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <p className="text-slate-400">Lead-Detail ({params.id}) wird in Step 4 implementiert …</p>
    </div>
  );
}
