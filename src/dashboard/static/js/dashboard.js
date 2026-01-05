// Voiseege Dashboard JavaScript
class DashboardApp {
    constructor() {
        this.currentPage = 1;
        this.itemsPerPage = 10;
        this.currentSaleId = null;
        
        this.initializeElements();
        this.bindEvents();
        this.loadInitialData();
    }
    
    initializeElements() {
        // DOM elements
        this.verificationFilter = document.getElementById('verification-filter');
        this.refreshBtn = document.getElementById('refresh-btn');
        this.addCongregantBtn = document.getElementById('add-congregant-btn');
        this.searchInput = document.getElementById('search-input');
        this.searchBtn = document.getElementById('search-btn');
        this.salesTbody = document.getElementById('sales-tbody');
        this.pagination = document.getElementById('pagination');
        this.totalRecordings = document.getElementById('total-recordings');
        this.totalSales = document.getElementById('total-sales');
        this.nextShabbat = document.getElementById('next-shabbat');
        this.unverifiedValue = document.getElementById('unverified-value');
        this.shabbatStatus = document.getElementById('shabbat-status');
        
        // Modal elements
        this.verificationModal = new bootstrap.Modal(document.getElementById('verificationModal'));
        this.modalBuyerName = document.getElementById('modal-buyer-name');
        this.modalAliyahType = document.getElementById('modal-aliyah-type');
        this.modalAmount = document.getElementById('modal-amount');
        this.modalTranscript = document.getElementById('modal-transcript');
        this.modalAudio = document.getElementById('modal-audio');
        this.modalNotes = document.getElementById('modal-notes');
        this.modalVerifySwitch = document.getElementById('modal-verify-switch');
        this.saveVerificationBtn = document.getElementById('save-verification-btn');
    }
    
    bindEvents() {
        // Button events
        this.refreshBtn.addEventListener('click', () => this.loadSales());
        this.addCongregantBtn.addEventListener('click', () => this.showAddCongregantModal());
        this.searchBtn.addEventListener('click', () => this.performSearch());
        this.searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.performSearch();
        });
        
        // Filter events
        this.verificationFilter.addEventListener('change', () => this.loadSales());
        
        // Modal events
        this.saveVerificationBtn.addEventListener('click', () => this.saveVerification());
    }
    
    async loadInitialData() {
        await this.loadSystemStatus();
        await this.loadSales();
        this.startStatusRefresh();
    }
    
    async loadSystemStatus() {
        try {
            const response = await fetch('/api/status');
            const data = await response.json();
            
            // Update system stats
            this.totalRecordings.textContent = data.system_stats.total_recordings;
            this.totalSales.textContent = data.system_stats.total_sales;
            this.unverifiedValue.textContent = data.system_stats.unverified_sales;
            
            // Update Shabbat status
            const isShabbat = data.shabbat_status.is_shabbat;
            const statusText = isShabbat ? 'SHABBAT ACTIVE' : 'SHABBAT INACTIVE';
            const statusClass = isShabbat ? 'shabbat-active' : 'shabbat-inactive';
            
            this.shabbatStatus.innerHTML = `
                <i class="fas fa-star-and-crescent"></i> 
                <span class="${statusClass}">${statusText}</span>
            `;
            
            // Update next Shabbat info
            this.nextShabbat.textContent = new Date(data.shabbat_status.next_shabbat_info.next_shabbat_start).toLocaleString();
        } catch (error) {
            console.error('Error loading system status:', error);
        }
    }
    
    async loadSales(page = 1) {
        this.currentPage = page;
        
        try {
            const verifiedFilter = this.verificationFilter.value;
            let url = `/api/aliyah-sales?limit=${this.itemsPerPage}&offset=${(page - 1) * this.itemsPerPage}`;
            
            if (verifiedFilter !== '') {
                url += `&verified=${verifiedFilter}`;
            }
            
            const response = await fetch(url);
            const sales = await response.json();
            
            this.renderSales(sales);
            this.updatePagination(sales.length);
        } catch (error) {
            console.error('Error loading sales:', error);
        }
    }
    
    renderSales(sales) {
        this.salesTbody.innerHTML = '';
        
        if (sales.length === 0) {
            this.salesTbody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center">No sales found</td>
                </tr>
            `;
            return;
        }
        
        sales.forEach(sale => {
            const row = document.createElement('tr');
            
            // Format confidence
            let confidenceClass = 'confidence-low';
            if (sale.confidence > 70) confidenceClass = 'confidence-high';
            else if (sale.confidence > 40) confidenceClass = 'confidence-medium';
            
            // Format verification status
            const statusClass = sale.verified ? 'status-verified' : 'status-unverified';
            const statusText = sale.verified ? 'Verified' : 'Unverified';
            
            row.innerHTML = `
                <td>${new Date(sale.created_at).toLocaleString()}</td>
                <td>${sale.congregant_name || 'Unknown'}</td>
                <td>${sale.aliyah_type}</td>
                <td>${sale.amount ? sale.amount + ' NIS' : 'N/A'}</td>
                <td><span class="${confidenceClass}">${sale.confidence ? sale.confidence.toFixed(1) + '%' : 'N/A'}</span></td>
                <td><span class="status-badge ${statusClass}">${statusText}</span></td>
                <td>
                    <button class="btn btn-sm btn-primary action-btn view-btn" data-id="${sale.id}">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="btn btn-sm btn-success action-btn verify-btn" data-id="${sale.id}" ${sale.verified ? 'disabled' : ''}>
                        <i class="fas fa-check"></i>
                    </button>
                </td>
            `;
            
            this.salesTbody.appendChild(row);
        });
        
        // Bind events to the new buttons
        document.querySelectorAll('.view-btn').forEach(btn => {
            btn.addEventListener('click', () => this.viewSale(btn.dataset.id));
        });
        
        document.querySelectorAll('.verify-btn').forEach(btn => {
            btn.addEventListener('click', () => this.verifySale(btn.dataset.id));
        });
    }
    
    updatePagination(count) {
        // For simplicity, we'll just show a basic pagination
        // In a real app, you'd calculate total pages and create proper pagination
        this.pagination.innerHTML = `
            <li class="page-item ${this.currentPage <= 1 ? 'disabled' : ''}">
                <a class="page-link" href="#" onclick="app.loadSales(${this.currentPage - 1})">Previous</a>
            </li>
            <li class="page-item active">
                <span class="page-link">${this.currentPage}</span>
            </li>
            <li class="page-item ${count < this.itemsPerPage ? 'disabled' : ''}">
                <a class="page-link" href="#" onclick="app.loadSales(${this.currentPage + 1})">Next</a>
            </li>
        `;
    }
    
    async viewSale(saleId) {
        try {
            const response = await fetch(`/api/aliyah-sales/${saleId}`);
            const sale = await response.json();
            
            this.populateModal(sale);
            this.currentSaleId = saleId;
            this.verificationModal.show();
        } catch (error) {
            console.error('Error loading sale:', error);
        }
    }
    
    async verifySale(saleId) {
        try {
            const response = await fetch(`/api/aliyah-sales/${saleId}`);
            const sale = await response.json();
            
            this.populateModal(sale);
            this.currentSaleId = saleId;
            this.verificationModal.show();
        } catch (error) {
            console.error('Error loading sale for verification:', error);
        }
    }
    
    populateModal(sale) {
        this.modalBuyerName.value = sale.congregant_name || 'Unknown';
        this.modalAliyahType.value = sale.aliyah_type;
        this.modalAmount.value = sale.amount ? `${sale.amount} NIS` : 'N/A';
        this.modalTranscript.value = sale.transcript || 'No transcript available';
        
        // Set up audio if available
        if (sale.audio_filename) {
            this.modalAudio.src = `/api/audio/${sale.audio_filename}`;
            this.modalAudio.load();
        } else {
            this.modalAudio.src = '';
            this.modalAudio.textContent = 'No audio available';
        }
        
        // Reset verification switch
        this.modalVerifySwitch.checked = sale.verified;
        this.modalNotes.value = sale.verification_notes || '';
    }
    
    async saveVerification() {
        if (!this.currentSaleId) return;
        
        const verified = this.modalVerifySwitch.checked;
        const notes = this.modalNotes.value;
        
        try {
            const response = await fetch(`/api/aliyah-sales/${this.currentSaleId}/verify`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    verified: verified,
                    notes: notes
                })
            });
            
            if (response.ok) {
                this.verificationModal.hide();
                this.loadSales(this.currentPage); // Reload current page
                this.loadSystemStatus(); // Update status counts
            } else {
                const error = await response.json();
                alert(`Error: ${error.error}`);
            }
        } catch (error) {
            console.error('Error saving verification:', error);
            alert('Error saving verification');
        }
    }
    
    performSearch() {
        // For now, just reload sales with the current filter
        // In a real app, you'd implement actual search functionality
        this.loadSales();
    }
    
    showAddCongregantModal() {
        // In a real app, you'd show a form to add a new congregant
        alert('Add Congregant functionality would be implemented here');
    }
    
    startStatusRefresh() {
        // Refresh system status every 30 seconds
        setInterval(() => {
            this.loadSystemStatus();
        }, 30000);
    }
}

// Initialize the app when the page loads
let app;
document.addEventListener('DOMContentLoaded', () => {
    app = new DashboardApp();
});