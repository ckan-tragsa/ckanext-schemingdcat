/**
 * A module that handles downloading BibTeX and RIS files from datasets DOI.
 *
 * @module dataset-citations
 */

document.addEventListener('DOMContentLoaded', () => {
    const downloadLinks = document.querySelectorAll('#download-bibtex, #download-ris');

    const handleDownload = async (event) => {
        event.preventDefault();
        const downloadLink = event.currentTarget;
        const url = downloadLink.href;
        const format = downloadLink.id === 'download-ris' ? 'ris' : 'bibtex';

        // Extract the DOI from the URL
        const doiMatch = url.match(/works\/(.*?)\/transform/);
        if (!doiMatch || doiMatch.length < 2) {
            alert('DOI not found in the URL.');
            return;
        }

        const doi = doiMatch[1];

        // Normalize the DOI by replacing invalid characters
        const normalizedDoi = doi.replace(/[\/:]/g, '-');

        try {
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error('Network response error');
            }
            const blob = await response.blob();
            const objectURL = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = objectURL;
            a.download = `${normalizedDoi}.${format === 'bibtex' ? 'bib' : 'ris'}`; // Assign normalized name with appropriate extension
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(objectURL);
        } catch (error) {
            console.error('Error downloading the file:', error);
            alert('There was an error downloading the file. Please try again.');
        }
    };

    downloadLinks.forEach((link) => {
        link.addEventListener('click', handleDownload);
    });
});