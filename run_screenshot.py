from utils import render_html

async def run_screenshot(project_id, page_id, variant_id):
    if (variant_id == "reference"):
        await render_html(f"{project_id}/pages/{page_id}/generated/reference.html")
    else:
        await render_html(f"{project_id}/pages/{page_id}/generated/{variant_id}/page.html")
        
    print(f"[screenshot] {project_id}.{page_id}.{variant_id} - finished")
